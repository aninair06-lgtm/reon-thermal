"""Shared, single-source-of-truth inputs for every model (network, OpenFOAM, Elmer).

Every value carries an input class:
  MP = manufacturer-published (REON), US = user-supplied (challenge brief),
  CAL = calibrated (fitted to our own 3D runs), AA = analyst-assumed (us).
See input_register.md for the full table and the missing-items list.
"""
import math

# ---------------- System (MP: REON EBS Na+ 30 kW / 60 kWh; 128 cells is US) ----------------
P_RATED_W = 30_000.0          # MP
E_RATED_WH = 60_000.0         # MP
N_CELLS = 128                 # US
N_MOD = 8                     # US (8 modules x 16 cells)
N_PER_MOD = 16                # US
T_DISCHARGE_S = 7200.0        # US (2 h)

# ---------------- Cabinet geometry (US/AA: REON has not confirmed) ----------------
CAB_W, CAB_D, CAB_H = 1.30, 0.40, 2.35       # x, y, z [m]  (US)
CELL_Y, CELL_X, CELL_Z = 0.1747, 0.0717, 0.207  # cell depth (y), thickness (x), height (z) [m] (US)
PAD_X = 0.0002                # 0.2 mm interface layer between large faces (US)
GAP_Z = 0.030                 # clear gap between modules (US)
MOD_LEN_ASSUMED = 1.17        # assumed module length (US)
MOD_LEN = N_PER_MOD * CELL_X + (N_PER_MOD - 1) * PAD_X   # 1.1502 m stack length
END_ALLOWANCE = MOD_LEN_ASSUMED - MOD_LEN                 # 0.0198 m -> two 9.9 mm end plates (AA)
Z_BOTTOM = 0.150              # floor-to-module-1 clearance: supply plenum + supports (AA)
X0 = 0.5 * (CAB_W - MOD_LEN)  # side clearance each side (0.0749 m; incl. the 9.9 mm end-plate allowance) (AA)
Y0 = 0.5 * (CAB_D - CELL_Y)   # front / rear plenum depth (0.11265 m) (AA)
PITCH_X = MOD_LEN / N_PER_MOD  # 0.071888 m mesh pitch used by 3D models (cell + share of pad)

def module_z0(m):              # m = 1..8, module 1 at the bottom
    return Z_BOTTOM + (m - 1) * (CELL_Z + GAP_Z)

Z_TOP_OF_STACK = module_z0(N_MOD) + CELL_Z   # 2.016 m
TOP_SPACE = CAB_H - Z_TOP_OF_STACK           # 0.334 m (inverter / top block lives here) (AA)

# Inlet / outlet (US positions, AA sizes; parameterised)
INLET = dict(face="front", z0=0.0, z1=0.150, x0=0.0, x1=CAB_W)   # bottom front, full width
OUTLET = dict(face="top", y0=CAB_D - Y0, y1=CAB_D, x0=0.0, x1=CAB_W)  # roof over rear plenum

# ---------------- Cell properties (US) ----------------
CELL_VOL = CELL_X * CELL_Y * CELL_Z          # 2.593e-3 m3
RHO_CELL = 1773.0
CP_CELL = 1050.0
CELL_MASS = RHO_CELL * CELL_VOL              # 4.60 kg
C_CELL = CELL_MASS * CP_CELL                 # 4.83 kJ/K
K_INPLANE = 25.0                             # y and z
K_THROUGH_BASE = 1.0                         # x (sweep 0.5, 1, 2, 3)
R_CONTACT = 0.0002 / 0.2 + 0.0003            # 0.0013 m2K/W (pad + two contacts), counted once (US)

# ---------------- Heat (US) ----------------
Q_NORMAL = 6.1        # W per cell at rated discharge
Q_AGED = 18.3         # W (3x resistance at the same current)
Q_BYPASS_IDEAL = 0.0

# ---------------- Electrical (AA: topology NOT published by REON) ----------------
# All-series string of 128 cells is our ASSUMPTION; the 128/115 current scaling is only valid for it.
V_NOM_CELL = 3.10      # V, typical Na-ion layered-oxide/hard-carbon nominal (AA)
CAP_AH = E_RATED_WH / (N_CELLS * V_NOM_CELL)   # 151 Ah implied (AA, derived)
I_RATED = P_RATED_W / (N_CELLS * V_NOM_CELL)   # 75.6 A
R_CELL_EFF = Q_NORMAL / I_RATED**2             # 1.07 mOhm effective heat resistance (CAL to the 6.1 W)
R_SWITCH = 0.25e-3     # Ohm per conducting cell switch (AA, sweep 0.1-0.5 mOhm)
R_CONN = 0.10e-3       # Ohm per cell-to-cell busbar joint (AA)
SOC_WINDOW = 1.00      # usable fraction of nameplate per cell (AA, sweep 0.9-1.05)
V_CELL_MIN, V_CELL_MAX = 1.5, 4.0   # V (AA, typical Na-ion); inverter DC window unknown

# ---------------- Air / walls / ambient (US + AA) ----------------
RHO_AIR, CP_AIR, K_AIR, MU_AIR, PR_AIR = 1.19, 1006.0, 0.0262, 1.83e-5, 0.71   # at ~22 C (CoolProp-equivalent constants)
Q_FORCED = 0.15        # m3/s (US)
T_SUPPLY_C = 20.0      # US
T_AMB_FORCED_C = 25.0  # US
WALL_T, WALL_RHO, WALL_CP, WALL_K = 0.0015, 7850.0, 490.0, 50.0   # 1.5 mm steel (AA)
WALL_AREA = 2 * (CAB_W * CAB_D + CAB_W * CAB_H + CAB_D * CAB_H)   # 9.03 m2
H_EXT = (5.0, 10.0)    # W/m2K (US), combined external convection+radiation
EPS_CELL = 0.8         # emissivity (AA; sweep 0.2-0.9)
EPS_WALL = 0.8
SIGMA = 5.670374e-8
Q_INVERTER = 750.0     # W top block (US)

def cell_id(m, c):
    return f"M{m:02d}_C{c:02d}"

if __name__ == "__main__":
    print(f"MOD_LEN={MOD_LEN:.4f} allowance={END_ALLOWANCE*1000:.1f} mm, X0={X0:.4f}, Y0={Y0:.5f}")
    print(f"stack top={Z_TOP_OF_STACK:.3f}, top space={TOP_SPACE:.3f}")
    print(f"cell vol={CELL_VOL:.4e}, mass={CELL_MASS:.3f}, C={C_CELL:.0f}, q'''={Q_NORMAL/CELL_VOL:.0f}")
    print(f"I={I_RATED:.1f} A, R={R_CELL_EFF*1e3:.3f} mOhm, Cap={CAP_AH:.1f} Ah, wall area={WALL_AREA:.2f}")
