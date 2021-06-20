import gurobipy as gp
from gurobipy import GRB

'''
not done
'''

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
        self.m = gp.Model("determin")

    def __def_sets(self):
        # hyper
        self.T_len = 10
        self.S_len = 6

        # sets
        self.T = range(self.T_len)
        self.S = range(self.S_len)

    def __def_parameters(self):
        self.C_S = 5
        self.C_H = 3
        self.C_CM = 0 #10
        self.C_PM = 0 #2
        self.T_PM = 2 #2
        self.T_CM = 4 #3
        self.H_max = 40
        self.H_I = 30
        self.B_I = 0
        self.S_I = 4
        self.R = 2
        self.M = 10000000
        self.W = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        self.D = [-1000, 7, 7, 7, 7, 7, 7, 7, 7, 7]

    def __def_decision_vars(self):
        self.x = self.m.addVars(self.T_len, vtype=GRB.INTEGER, lb=0, name="x") #ub=?
        self.z_PM = self.m.addVars(self.T_len, vtype=GRB.BINARY, name="z_PM")
        self.z_CM = self.m.addVars(self.T_len, vtype=GRB.BINARY, name="z_CM")
        self.s = self.m.addVars(self.T_len, vtype=GRB.INTEGER, lb=0, ub=5, name="s")
        self.z_P = self.m.addVars(self.T_len, vtype=GRB.BINARY, name="z_P")
        self.b = self.m.addVars(self.T_len, vtype=GRB.INTEGER, lb=0, name="b")
        self.h = self.m.addVars(self.T_len, vtype=GRB.INTEGER, lb=0, name="h")
    
    def __def_objectives(self):
        holding_cost = gp.quicksum(self.C_H * self.h[t] for t in self.T)
        stockout_cost = gp.quicksum(self.C_S * self.b[t] for t in self.T)
        PM_cost = gp.quicksum(self.C_PM * self.z_PM[t] for t in self.T)
        CM_cost = gp.quicksum(self.C_CM * self.z_CM[t] for t in self.T)

        self.m.setObjective(holding_cost + stockout_cost + PM_cost + CM_cost, GRB.MINIMIZE)

    def __def_constraints(self):
        # c1: 初始化參數
        self.m.addConstr(self.x[0] == 0, name="c1")
        self.m.addConstr(self.z_PM[0] == 0, name="c1")
        self.m.addConstr(self.z_CM[0] == 0, name="c1")
        self.m.addConstr(self.z_P[0] == 0, name="c1")
        self.m.addConstr(self.h[0] == self.H_I, name="c1")
        self.m.addConstr(self.b[0] == self.B_I, name="c1")
        self.m.addConstr(self.s[0] == self.S_I, name="c1")

        for t in self.T:
        # c2: 在時間週期t開始PM或CM，後續時間不能再開始PM或CM
            self.m.addConstr(
                (1 - self.z_PM[t]) * self.M >= gp.quicksum(self.z_PM[t_prime] + self.z_CM[t_prime] 
                for t_prime in range(t+1, t+self.T_PM) if t_prime in self.T), name="c2"
            )
            self.m.addConstr(
                (1 - self.z_CM[t]) * self.M >= gp.quicksum(self.z_PM[t_prime] + self.z_CM[t_prime] 
                for t_prime in range(t+1, t+self.T_CM) if t_prime in self.T), name="c2"
            )
            # print("t =", t, [t_prime for t_prime in range(t+1, t+self.T_CM) if t_prime in self.T])


        # c3: 在時間週期t開始PM或CM，後續時間不能生產
            self.m.addConstr(
                (1 - self.z_PM[t]) * self.M >= gp.quicksum(self.x[t_prime] 
                for t_prime in range(t, t+self.T_PM) if t_prime in self.T), name="c3"
            )
            self.m.addConstr(
                (1 - self.z_CM[t]) * self.M >= gp.quicksum(self.x[t_prime] 
                for t_prime in range(t, t+self.T_CM) if t_prime in self.T), name="c3"
            )
            # print("t =", t, [t_prime for t_prime in range(t, t+self.T_CM) if t_prime in self.T])
            # continue
        # c4: 一個週期只能開始PM或CM其中一個
            self.m.addConstr(
                self.z_PM[t] + self.z_CM[t] + self.z_P[t] <= 1, name="c4"
            )
    
        # c5: 若且唯若機台壞掉要CM
            self.m.addConstr(
                (self.S_len - 1) - self.s[t] <= (1 - self.z_CM[t]) * self.M, name="c5"
            )
            self.m.addConstr(
                1 - ((self.S_len - 1) - self.s[t]) * self.M <= self.z_CM[t], name="c5"
            )

            if t != self.T_len - 1:
        # c6: 開始維護後，下一期機台狀態更新
                self.m.addConstr(
                    (1 - self.z_CM[t]) * self.M >= self.s[t+1], name="c6"
                )
                self.m.addConstr(
                    self.s[t+1] >= (self.s[t] - self.R) - (1 - self.z_PM[t]), name="c6"
                )

        # c7: 有生產時的機台狀態更新
                self.m.addConstr(
                    self.s[t+1] >= self.s[t] + self.W[t] - (1 - self.z_P[t]) * self.M, name="c7"
                )
                # self.m.addConstr(
                #     self.s[t+1] <= self.s[t] + self.W[t] + (1 - self.z_P[t]) * self.M
                # )
        # c8: 定義是否開機
            self.m.addConstr(
                self.z_P[t] * self.M >= self.x[t], name="c8"
            )
            self.m.addConstr(
                self.x[t] >= self.z_P[t], name="c8"
            )

        # c9: 無生產且無PM且無CM時的機台狀態延續
            if t != self.T_len - 1:
                self.m.addConstr(
                    self.s[t+1] >= self.s[t] - (self.z_P[t] + self.z_CM[t] + self.z_PM[t]) * self.M, name="c9"
                )
                self.m.addConstr(
                    self.s[t+1] <= self.s[t] + (self.z_P[t] + self.z_CM[t] + self.z_PM[t]) * self.M, name="c9"
                )

        # c10: 機台狀態生產量上限
            self.m.addConstr(
                self.x[t] <= 2 * (5 - self.s[t]), name="c10"
            )

        # c11: 供給與訂單需求
            if t != 0:
                self.m.addConstr(
                    self.h[t] == 0.7 * self.x[t] + self.h[t-1] + self.b[t] - self.D[t] - self.b[t-1], name="c11"
                )
        # c12: 存貨上限
            self.m.addConstr(self.h[t] <= self.H_max, name="c12")

    def optimize(self):
        self.m.write('model.lp')
        self.m.setParam('TimeLimit', 120)     
        self.m.optimize()
        self.m.write("out.sol")
        self.__get_sol()

    def __get_sol(self):
        self.x_sol = self.m.getAttr('x', self.x)
        self.z_PM_sol = self.m.getAttr('x', self.z_PM)
        self.z_CM_sol = self.m.getAttr('x', self.z_CM)
        self.s_sol = self.m.getAttr('x', self.s)
        self.z_P_sol = self.m.getAttr('x', self.z_P)
        self.b_sol = self.m.getAttr('x', self.b)
        self.h_sol = self.m.getAttr('x', self.h)

    def display_param(self):
        # print("period len:", self.T_len)
        # print()
        pass

    def display_sol(self):
        print("x: {}".format([int(self.x_sol[t]) for t in self.x_sol]))
        print("z_PM: {}".format([int(self.z_PM_sol[t]) for t in self.z_PM_sol]))
        print("z_CM: {}".format([int(self.z_CM_sol[t]) for t in self.z_CM_sol]))
        print("s: {}".format([int(self.s_sol[t]) for t in self.s_sol]))
        print("z_P: {}".format([int(self.z_P_sol[t]) for t in self.z_P_sol]))
        print("b: {}".format([int(self.b_sol[t]) for t in self.b_sol]))
        print("h: {}".format([int(self.h_sol[t]) for t in self.h_sol]))
    