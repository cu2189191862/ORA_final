import numpy as np
import gurobipy as gp
from gurobipy import GRB
from numpy.core.fromnumeric import shape

class Model:
    def __init__(self):
        self.__def_model()
        self.__def_sets()
        self.__def_parameters()
        self.__def_decision_vars()
        self.__def_objectives()
        self.__def_constraints()
        pass
    
    def __def_model(self):
        self.model = gp.Model("determin")

    def __def_sets(self):
        # hyper
        self.T_len = 10
        self.S_len = 6

        # sets
        self.T = range(self.T_len)
        self.S = range(self.S_len)

    def __def_parameters(self):
        demand_mu = 4
        demand_sigma= 1

        self.C_S = 5
        self.C_H = 3
        self.C_CM = 0 # 10
        self.C_PM = 0 # 2
        self.T_PM = 2 # 2
        self.T_CM = 4 # 3
        self.H_max = 40
        self.H_I = 30
        self.B_I = 0
        self.S_I = 4
        self.R = 2
        self.M = 10000000
        self.m = 0.0001
        self.W_P = [0.18126924692201818, 0.3296799539643607, 0.4511883639059736, 0.5506710358827784, 0.6321205588285577, 0]
        self.W = np.random.uniform(low=0.0, high=1.0, size=self.T_len).tolist()
        self.D = np.random.normal(loc=demand_mu, scale=demand_sigma, size=(self.T_len)).tolist()
        # print(self.W)
        # print(self.D)



    def __def_decision_vars(self):
        self.x = self.model.addVars(self.T_len, vtype=GRB.CONTINUOUS, lb=0, name="x") #ub=?
        self.z_PM = self.model.addVars(self.T_len, vtype=GRB.BINARY, name="z_PM")
        self.z_CM = self.model.addVars(self.T_len, vtype=GRB.BINARY, name="z_CM")
        self.s = self.model.addVars(self.T_len, vtype=GRB.INTEGER, lb=0, ub=5, name="s")
        self.z_P = self.model.addVars(self.T_len, vtype=GRB.BINARY, name="z_P")
        self.z_S = self.model.addVars(self.S_len, self.T_len, vtype=GRB.BINARY, name="z_S")
        self.z_W = self.model.addVars(self.T_len, vtype=GRB.BINARY, name="z_W")
        self.b = self.model.addVars(self.T_len, vtype=GRB.CONTINUOUS, lb=0, name="b")
        self.h = self.model.addVars(self.T_len, vtype=GRB.CONTINUOUS, lb=0, name="h")
    
    def __def_objectives(self):
        holding_cost = gp.quicksum(self.C_H * self.h[t] for t in self.T)
        stockout_cost = gp.quicksum(self.C_S * self.b[t] for t in self.T)
        PM_cost = gp.quicksum(self.C_PM * self.z_PM[t] for t in self.T)
        CM_cost = gp.quicksum(self.C_CM * self.z_CM[t] for t in self.T)

        self.model.setObjective(holding_cost + stockout_cost + PM_cost + CM_cost, GRB.MINIMIZE)

    def __def_constraints(self):
        # c1: 初始化參數
        self.model.addConstr(self.x[0] == 0, name="c1")
        self.model.addConstr(self.z_PM[0] == 0, name="c1")
        self.model.addConstr(self.z_CM[0] == 0, name="c1")
        self.model.addConstr(self.z_P[0] == 0, name="c1")
        self.model.addConstr(self.h[0] == self.H_I, name="c1")
        self.model.addConstr(self.b[0] == self.B_I, name="c1")
        self.model.addConstr(self.s[0] == self.S_I, name="c1")

        for t in self.T:
        # c2: 在時間週期t開始PM或CM，後續時間不能再開始PM或CM
            self.model.addConstr(
                (1 - self.z_PM[t]) * self.M >= gp.quicksum(self.z_PM[t_prime] + self.z_CM[t_prime] 
                for t_prime in range(t+1, t+self.T_PM) if t_prime in self.T), name="c2"
            )
            self.model.addConstr(
                (1 - self.z_CM[t]) * self.M >= gp.quicksum(self.z_PM[t_prime] + self.z_CM[t_prime] 
                for t_prime in range(t+1, t+self.T_CM) if t_prime in self.T), name="c2"
            )

        # c3: 在時間週期t開始PM或CM，後續時間不能生產
            self.model.addConstr(
                (1 - self.z_PM[t]) * self.M >= gp.quicksum(self.x[t_prime] 
                for t_prime in range(t, t+self.T_PM) if t_prime in self.T), name="c3"
            )
            self.model.addConstr(
                (1 - self.z_CM[t]) * self.M >= gp.quicksum(self.x[t_prime] 
                for t_prime in range(t, t+self.T_CM) if t_prime in self.T), name="c3"
            )

        # c4: 一個週期只能開始PM或CM其中一個
            self.model.addConstr(
                self.z_PM[t] + self.z_CM[t] + self.z_P[t] <= 1, name="c4"
            )
    
        # c5: 若且唯若機台壞掉要CM
            self.model.addConstr(
                (self.S_len - 1) - self.s[t] <= (1 - self.z_CM[t]) * self.M, name="c5"
            )
            self.model.addConstr(
                1 - ((self.S_len - 1) - self.s[t]) * self.M <= self.z_CM[t], name="c5"
            )

            if t != self.T_len - 1:
        # c6: 開始維護後，下一期機台狀態更新
                self.model.addConstr(
                    (1 - self.z_CM[t]) * self.M >= self.s[t+1], name="c6"
                )
                self.model.addConstr(
                    self.s[t+1] >= (self.s[t] - self.R) - (1 - self.z_PM[t]), name="c6"
                )

        # c7: 有生產時的機台狀態更新
                self.model.addConstr(
                    self.s[t+1] >= self.s[t] + self.z_W[t] - (1 - self.z_P[t]) * self.M, name="c7"
                )
                self.model.addConstr(
                    self.s[t+1] <= self.s[t] + self.z_W[t] + (1 - self.z_P[t]) * self.M, name="c7"
                )

        # c8: 定義是否開機
            self.model.addConstr(
                self.z_P[t] * self.M >= self.x[t], name="c8"
            )
            self.model.addConstr(
                self.x[t] >= self.z_P[t], name="c8"
            )

        # c9: 無生產且無PM且無CM時的機台狀態延續
            if t != self.T_len - 1:
                self.model.addConstr(
                    self.s[t+1] >= self.s[t] - (self.z_P[t] + self.z_CM[t] + self.z_PM[t]) * self.M, name="c9"
                )
                self.model.addConstr(
                    self.s[t+1] <= self.s[t] + (self.z_P[t] + self.z_CM[t] + self.z_PM[t]) * self.M, name="c9"
                )

        # c10: 機台狀態生產量上限
            self.model.addConstr(
                self.x[t] <= 2 * (5 - self.s[t]), name="c10"
            )

        # c11: 供給與訂單需求
            if t != 0:
                self.model.addConstr(
                    self.h[t] == self.x[t] + self.h[t-1] + self.b[t] - self.D[t] - self.b[t-1], name="c11"
                )
        # c12: 存貨上限
            self.model.addConstr(self.h[t] <= self.H_max, name="c12")

        # c13: 定義是狀態幾
            for s_hat in self.S:
                self.model.addConstr(s_hat - self.s[t] <= self.M * (1 - self.z_S[s_hat, t]), name="c13")
                self.model.addConstr(self.s[t] - s_hat <= self.M * (1 - self.z_S[s_hat, t]), name="c13")
            self.model.addConstr(gp.quicksum(self.z_S[s_hat, t] for s_hat in self.S) == 1, name="c13")

        # c14: 依照狀態進行對應的衰退判斷
            self.model.addConstr(self.z_W[t] >= gp.quicksum(self.z_S[s_hat, t] * self.W_P[s_hat] for s_hat in self.S) - self.W[t], name="c14")
            self.model.addConstr(-self.M * (1 - self.z_W[t]) <= gp.quicksum(self.z_S[s_hat, t] * self.W_P[s_hat] for s_hat in self.S) - self.W[t], name="c14")




    def optimize(self):
        self.model.write('model.lp')
        self.model.setParam('TimeLimit', 120)     
        self.model.optimize()
        self.model.write("out.sol")
        self.__get_sol()

    def __get_sol(self):
        self.x_sol = self.model.getAttr('x', self.x)
        self.z_PM_sol = self.model.getAttr('x', self.z_PM)
        self.z_CM_sol = self.model.getAttr('x', self.z_CM)
        self.s_sol = self.model.getAttr('x', self.s)
        self.z_P_sol = self.model.getAttr('x', self.z_P)
        self.z_S_sol = self.model.getAttr('x', self.z_S)
        self.z_W_sol = self.model.getAttr('x', self.z_W)
        self.b_sol = self.model.getAttr('x', self.b)
        self.h_sol = self.model.getAttr('x', self.h)

    def log_params(self):
        D = [round(d, 3) for d in self.D]
        W = [round(w, 3) for w in self.W]
        W_P = [round(w_p, 3) for w_p in self.W_P]
        print("Params")
        print("\tD: {}".format(D))
        print("\tW: {}".format(W))
        print("\tW_P: {}".format(W_P))

    def log_sol(self):
        print("Solution")
        print("\tx: {}".format([round(self.x_sol[t], 3) for t in self.T]))
        print("\tz_PM: {}".format([int(self.z_PM_sol[t]) for t in self.T]))
        print("\tz_CM: {}".format([int(self.z_CM_sol[t]) for t in self.T]))
        print("\ts: {}".format([int(self.s_sol[t]) for t in self.T]))
        print("\tz_P: {}".format([int(self.z_P_sol[t]) for t in self.T]))
        # print("\tz_S: {}".format([[int(self.z_S_sol[s_hat, t]) for t in self.T] for s_hat in self.S]))
        print("\tz_W: {}".format([int(self.z_W_sol[t]) for t in self.T]))
        print("\tb: {}".format([round(self.b_sol[t], 3) for t in self.T]))
        print("\th: {}".format([round(self.h_sol[t], 3) for t in self.T]))

    def dump_results(self, output_path):
        D = [round(d, 3) for d in self.D]
        W = [round(w, 3) for w in self.W]
        W_P = [round(w_p, 3) for w_p in self.W_P]

        with open(output_path, 'a') as f:
            f.write("Params\n")
            f.write("\tD: {}\n".format(D))
            f.write("\tW: {}\n".format(W))
            f.write("\tW_P: {}\n".format(W_P))

            f.write("Solution\n")
            f.write("\tx: {}\n".format([round(self.x_sol[t], 3) for t in self.T]))
            f.write("\tz_PM: {}\n".format([int(self.z_PM_sol[t]) for t in self.T]))
            f.write("\tz_CM: {}\n".format([int(self.z_CM_sol[t]) for t in self.T]))
            f.write("\ts: {}\n".format([int(self.s_sol[t]) for t in self.T]))
            f.write("\tz_P: {}\n".format([int(self.z_P_sol[t]) for t in self.T]))
            # f.write("\tz_S: {}".format([[int(self.z_S_sol[s_hat, t]) for t in self.T] for s_hat in self.S]))
            f.write("\tz_W: {}\n".format([int(self.z_W_sol[t]) for t in self.T]))
            f.write("\tb: {}\n".format([round(self.b_sol[t], 3) for t in self.T]))
            f.write("\th: {}\n".format([round(self.h_sol[t], 3) for t in self.T]))


    