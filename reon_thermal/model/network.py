"""Cell-resolved electrical-thermal network of the REON EBS cabinet (Stage 1 model).

* 128 cell nodes (volume-mean temperature, thermal mass 4.83 kJ/K each), anisotropic conduction
  between neighbouring cells through the 0.0013 m2K/W interface (counted once).
* Wall nodes: front / rear / left / right walls in 10 height segments + floor + roof (1.5 mm steel).
* Air is quasi-steady (its heat capacity is <0.3 % of the cells'): every air stream is marched
  segment by segment with an exact epsilon-NTU update, so heat given to air = enthalpy rise exactly.
  - forced: front plenum -> 9 cross channels (bottom space, 7 gaps, top space) -> rear plenum -> outlet,
    plus two side-clearance bypass streams.
  - passive (sealed): buoyant loop - up along the hot cell faces, across the gaps by exchange,
    down along the cool walls (lagged one step; the lag is booked as loop storage in the energy balance).
* Surface-to-surface radiation (sigma T^4, explicit), external h on walls only (no double count).
* Electrical (optional): all-series string ASSUMED (REON has not published topology), OCV(SOC),
  constant power / constant current / derated power, per-cell resistance, bypass-switch and
  busbar losses as separate heat sources, SOC tracking and energy feasibility.
* Everything carries a leading batch dimension B, so the same code runs 1 case on the CPU or
  10^4-10^5 cases at once on the GPU (CuPy).
"""
import math
import numpy as _np
import params as P

def get_xp(gpu):
    if gpu:
        import cupy
        return cupy
    return _np

NM, NC = P.N_MOD, P.N_PER_MOD
NSEG = 10   # wall/air height segments: 0 bottom space, 1..8 module levels (module + gap above), 9 top space

# ---- fixed geometry -------------------------------------------------------------------------
A_TB = P.CELL_X * P.CELL_Y          # top/bottom face of a cell   0.01253 m2
A_FR = P.CELL_X * P.CELL_Z          # front/rear face             0.01484 m2
A_SD = P.CELL_Y * P.CELL_Z          # large (x) face              0.03616 m2
LXH, LYH, LZH = P.CELL_X / 2, P.CELL_Y / 2, P.CELL_Z / 2
SEG_H = _np.array([P.Z_BOTTOM] + [P.CELL_Z + P.GAP_Z] * 7 + [P.CELL_Z, P.TOP_SPACE])   # sums to 2.35
assert abs(SEG_H.sum() - P.CAB_H) < 1e-9

DEFAULTS = dict(
    mode="forced",            # forced | passive
    kx=P.K_THROUGH_BASE, k_in=P.K_INPLANE, r_contact=P.R_CONTACT,
    flow=P.Q_FORCED, T_supply=P.T_SUPPLY_C, T_amb=P.T_AMB_FORCED_C, T_init=None,
    h_ext=5.0, eps=P.EPS_CELL, eps_wall=P.EPS_WALL,
    f_side=0.15,              # share of forced flow through the two side clearances (CAL from 3D)
    w_ch=None,                # share of main flow through channel j=0..8 (CAL from 3D)
    h_mult=1.0,               # multiplier on all internal convection coefficients (CAL)
    h_gap_mult=1.0,           # extra multiplier on the 7 inter-module gaps, forced mode (CAL)
    G_ex_forced=0.0,          # forced mode: gap <-> plenum exchange conductance per cell column [W/K] (CAL)
    cap_scale=1.0,            # scales cell+wall heat capacity (ONLY for pseudo-transient steady calibration)
    G_hp=0.0,                 # Stage-4 idea: heat pipe from every cell to the rear wall [W/K per cell]
    pcm_kg=0.0, pcm_L=200e3, pcm_Tm=46.0, pcm_dT=3.0,   # Stage-4 idea: phase-change plates in the gaps [kg per cell]
    cc_beta=0.475,            # lumped through-cell conduction factor (CAL: Elmer resolved module, mean err 0.44 K)
    tint_gamma=0.11,          # interior-peak factor for heat crossing a cell (CAL: Elmer, peak err 0.001 K)
    Q_circ=0.03,              # passive buoyant loop flow [m3/s] (CAL)
    G_ex=0.6,                 # passive gap<->plenum exchange conductance per gap [W/K] (CAL)
    h_gap_nat=1.5,            # passive h on faces inside the 30 mm gaps (CAL)
    G_sup=0.2,                # support conductance, each module end to the side wall [W/K] (AA)
    view_gap=0.85, view_wall=0.9,
    Q_inverter=0.0,           # W released into the top-space air
    solar_roof=0.0, solar_side=0.0,   # absorbed solar W/m2 on roof and the right wall (function of time allowed)
    # electrical
    elec=False, elec_mode="power", P_target=P.P_RATED_W, I_target=P.I_RATED,
    r_mult=None,              # per-cell resistance multiplier [B,8,16] (aged cell = 3)
    cap_mult=None,            # per-cell capacity multiplier
    r_switch=P.R_SWITCH, r_conn=0.0, soc0=1.0, soc_min=0.0,
    heat_scale=1.0,
    stop_on_empty=True, bypass_empty=False, n_min_active=100,
)

class Network:
    def __init__(self, B=1, gpu=False, **kw):
        self.xp = xp = get_xp(gpu)
        self.B = B
        o = dict(DEFAULTS); o.update(kw); self.o = o
        f = lambda v: xp.asarray(v, dtype=xp.float64) * xp.ones(B)            # per-batch scalar
        self.kx, self.kin, self.rc = f(o["kx"]), f(o["k_in"]), f(o["r_contact"])
        self.eps, self.epsw = f(o["eps"]), f(o["eps_wall"])
        self.hext, self.flow = f(o["h_ext"]), f(o["flow"])
        self.Tsup, self.Tamb = f(o["T_supply"]), f(o["T_amb"])
        self.hm, self.Qc, self.Gex, self.hgap = f(o["h_mult"]), f(o["Q_circ"]), f(o["G_ex"]), f(o["h_gap_nat"])
        self.hmg, self.Gexf = f(o["h_gap_mult"]), f(o["G_ex_forced"])
        self.Gsup, self.fside = f(o["G_sup"]), f(o["f_side"])
        self.heat_scale = f(o["heat_scale"])
        self.forced = o["mode"] == "forced"
        w = o["w_ch"] if o["w_ch"] is not None else [0.15] + [0.1] * 7 + [0.15]
        w = xp.asarray(w, dtype=xp.float64)
        self.w = (w / w.sum(axis=-1, keepdims=True)) * xp.ones((B, 9))
        # conductances (batch)
        # cell-cell through x [B]; beta=0.475 CALIBRATED to the resolved Elmer module (aged-cell spreading)
        self.Gcc = A_SD / (o["cc_beta"] * 2 * LXH / self.kx + self.rc)
        self.Rint_x = LXH / (3 * self.kx * A_SD)                            # mean->x-face, generation-driven
        self.Rint_y = LYH / (3 * self.kin * A_FR)
        self.Rint_z = LZH / (3 * self.kin * A_TB)
        # radiation effective emissivities
        self.e_cc = 1.0 / (2.0 / self.eps - 1.0) * o["view_gap"]
        self.e_cw = 1.0 / (1.0 / self.eps + 1.0 / self.epsw - 1.0) * o["view_wall"]
        # walls
        self.Aw_front = P.CAB_W * SEG_H.copy()
        self.Aw_rear = P.CAB_W * SEG_H.copy()
        self.Aw_side = P.CAB_D * SEG_H.copy()
        self.A_floor = P.CAB_W * P.CAB_D
        self.A_roof = P.CAB_W * P.CAB_D
        if self.forced:     # grilles are not wall
            self.Aw_front[0] -= P.CAB_W * (P.INLET["z1"] - P.INLET["z0"])
            self.A_roof -= P.CAB_W * (P.OUTLET["y1"] - P.OUTLET["y0"])
        cw = P.WALL_RHO * P.WALL_CP * P.WALL_T
        # zero-area segments (grilles) get a token capacity: all their fluxes are zero anyway
        self.Cw_front, self.Cw_rear, self.Cw_side = (xp.asarray(_np.maximum(a * cw, 1.0)) for a in (self.Aw_front, self.Aw_rear, self.Aw_side))
        self.Cw_floor, self.Cw_roof = self.A_floor * cw, self.A_roof * cw
        self.wall_area = self.Aw_front.sum() + self.Aw_rear.sum() + 2 * self.Aw_side.sum() + self.A_floor + self.A_roof
        # cells
        self.Ccell = P.C_CELL * o["cap_scale"] * xp.ones((B, NM, NC))
        if o.get("ccell_mult") is not None:
            self.Ccell = self.Ccell * xp.asarray(o["ccell_mult"])
        self.Cw_front, self.Cw_rear, self.Cw_side = (c * o["cap_scale"] for c in (self.Cw_front, self.Cw_rear, self.Cw_side))
        self.Cw_floor, self.Cw_roof = self.Cw_floor * o["cap_scale"], self.Cw_roof * o["cap_scale"]
        self.Aw_front_x, self.Aw_rear_x, self.Aw_side_x = (xp.asarray(a) for a in (self.Aw_front, self.Aw_rear, self.Aw_side))
        # electrical
        self.elec = o["elec"]
        self.rmult = xp.ones((B, NM, NC)) if o["r_mult"] is None else xp.asarray(o["r_mult"]) * xp.ones((B, NM, NC))
        self.cmult = xp.ones((B, NM, NC)) if o["cap_mult"] is None else xp.asarray(o["cap_mult"]) * xp.ones((B, NM, NC))
        self.reset(o["T_init"])

    # ------------------------------------------------------------------------------------------
    def reset(self, T_init=None):
        xp, B = self.xp, self.B
        T0 = self.Tamb if T_init is None else xp.asarray(T_init, dtype=xp.float64) * xp.ones(B)
        self.Tc = T0[:, None, None] * xp.ones((B, NM, NC))
        Tw0 = self.Tamb if T_init is None else T0
        self.Twf = Tw0[:, None] * xp.ones((B, NSEG)); self.Twr = self.Twf.copy()
        self.Twl = self.Twf.copy(); self.Twrt = self.Twf.copy()
        self.Tfl = Tw0.copy(); self.Tro = Tw0.copy()
        self.T_ret = T0.copy()          # passive loop return temperature
        self.soc = self.o["soc0"] * xp.ones((B, NM, NC))
        self.bypass = xp.zeros((B, NM, NC), dtype=bool)
        self.running = xp.ones(B, dtype=bool)
        self.t = 0.0
        self.E = {k: xp.zeros(B) for k in ("gen", "store", "ext", "enth", "loop", "elec_out", "loss_sw", "loss_conn")}
        self.Tmax_hist = []
        self.Q_inv = xp.asarray(self.o["Q_inverter"], dtype=xp.float64) * xp.ones(B)     # per batch
        self.sol_mult = xp.asarray(self.o.get("solar_mult", 1.0), dtype=xp.float64) * xp.ones(B)

    # ---- helpers ----
    def h_forced(self, Q, area, Dh, L, xp):
        """Mean h for flow through a duct section: laminar developing (Stephan) or Gnielinski."""
        V = Q / area
        nu = P.MU_AIR / P.RHO_AIR
        Re = xp.maximum(V * Dh / nu, 1.0)
        xs = L / (Dh * Re * P.PR_AIR)
        Nu_lam = 7.55 + 0.024 * xs ** -1.14 / (1 + 0.0358 * P.PR_AIR ** 0.17 * xs ** -0.64)
        fD = (0.79 * xp.log(xp.maximum(Re, 2300.0)) - 1.64) ** -2
        Nu_t = (fD / 8) * (Re - 1000) * P.PR_AIR / (1 + 12.7 * (fD / 8) ** 0.5 * (P.PR_AIR ** (2 / 3) - 1))
        a = xp.clip((Re - 2300.0) / 1700.0, 0.0, 1.0)            # blend 2300..4000
        Nu = (1 - a) * Nu_lam + a * xp.maximum(Nu_t, Nu_lam)
        return Nu * P.K_AIR / Dh

    @staticmethod
    def h_nat_v(dT, L, xp):
        dT = xp.maximum(xp.abs(dT), 0.5)
        return xp.maximum(1.42 * (dT / L) ** 0.25, 1.31 * dT ** (1 / 3) * 0.75)

    @staticmethod
    def march(T_in, W, G, Ts, xp):
        """epsilon-NTU through surfaces G[...,k] at Ts[...,k]; returns T_out, Q per surface (W into air)."""
        Gs = G.sum(-1)
        Tse = (G * Ts).sum(-1) / xp.maximum(Gs, 1e-12)
        T_out = Tse - (Tse - T_in) * xp.exp(-Gs / xp.maximum(W, 1e-12))
        Qt = W * (T_out - T_in)
        Tref = Tse - Qt / xp.maximum(Gs, 1e-12)
        return T_out, G * (Ts - Tref[..., None]), Tref

    # ------------------------------------------------------------------------------------------
    def heat(self, dt):
        """Per-cell heat [B,8,16] and string state for this step."""
        xp, o = self.xp, self.o
        if not self.elec:
            q = self.q_presc if hasattr(self, "q_presc") else P.Q_NORMAL * xp.ones_like(self.Tc)
            q = xp.where(self.bypass, self.q_bypass if hasattr(self, "q_bypass") else 0.0, q)
            self.I = xp.full(self.B, xp.nan); self.V = xp.full(self.B, xp.nan); self.Pout = xp.full(self.B, xp.nan)
            return q * self.heat_scale[:, None, None] * self.running[:, None, None]
        act = (~self.bypass) & (self.soc > o["soc_min"])
        if o["bypass_empty"]:
            self.bypass = self.bypass | (self.soc <= o["soc_min"])
            act = ~self.bypass
        ocv = 2.55 + 1.15 * xp.clip(self.soc, 0, 1)                        # AA: sloped Na-ion OCV
        Rcell = P.R_CELL_EFF * self.rmult                                   # incl. series switch (cal. to 6.1 W)
        nact = act.sum((1, 2))
        Rpath = (Rcell * act).sum((1, 2)) + o["r_switch"] * (~act).sum((1, 2)) + o["r_conn"] * (P.N_CELLS - 1)
        Voc = (ocv * act).sum((1, 2))
        if o["elec_mode"] == "current":
            I = o["I_target"] * xp.ones(self.B)
        else:
            Pt = o["P_target"] * xp.ones(self.B)
            disc = Voc ** 2 - 4 * Rpath * Pt
            I = (Voc - xp.sqrt(xp.maximum(disc, 0))) / (2 * Rpath)
        ok = self.running & (nact >= o["n_min_active"])
        I = xp.where(ok, I, 0.0)
        self.running = ok
        q = xp.where(act, I[:, None, None] ** 2 * Rcell, I[:, None, None] ** 2 * o["r_switch"])
        if o["r_conn"] > 0:
            qj = I ** 2 * o["r_conn"]
            q = q + qj[:, None, None]                                       # one joint per cell (book-kept at the cell)
            self.E["loss_conn"] += qj * P.N_CELLS * dt
        self.E["loss_sw"] += (I ** 2 * o["r_switch"] * (~act).sum((1, 2))) * dt
        cap = P.CAP_AH * self.cmult * 3600.0
        self.soc = self.soc - xp.where(act, I[:, None, None], 0.0) * dt / cap
        self.I, self.V = I, Voc - I * Rpath
        self.Pout = self.I * self.V
        self.E["elec_out"] += self.Pout * dt
        if o["stop_on_empty"] and not o["bypass_empty"]:
            self.running = self.running & ~((self.soc <= o["soc_min"]) & ~self.bypass).any((1, 2))
        return q * self.heat_scale[:, None, None]

    # ------------------------------------------------------------------------------------------
    def step(self, dt, record=False):
        xp, B = self.xp, self.B
        K = 273.15
        Tc = self.Tc
        sig = P.SIGMA
        q = self.heat(dt)
        Qn = xp.zeros_like(Tc)                     # net heat into each cell
        Qn += q
        # cell-cell conduction in x
        Gcc = self.Gcc[:, None, None]
        dq = Gcc * (Tc[:, :, 1:] - Tc[:, :, :-1])  # into left cell from right
        Qn[:, :, :-1] += dq; Qn[:, :, 1:] -= dq
        Qnb = xp.zeros_like(Tc); Qnb[:, :, :-1] += dq; Qnb[:, :, 1:] -= dq
        # radiation across gaps (top face of m <-> bottom face of m+1), floor, roof
        T4 = (Tc + K) ** 4
        rg = self.e_cc[:, None, None] * sig * A_TB * (T4[:, 1:] - T4[:, :-1])
        Qn[:, :-1] += rg; Qn[:, 1:] -= rg
        Qrad = xp.zeros_like(Tc); Qrad[:, :-1] += rg; Qrad[:, 1:] -= rg   # (sign: + = into cell)
        ecw = self.e_cw
        Twf4, Twr4 = (self.Twf + K) ** 4, (self.Twr + K) ** 4
        rf = ecw[:, None, None] * sig * A_FR * (Twf4[:, 1:9, None] - T4)       # front wall seg m+1
        rr = ecw[:, None, None] * sig * A_FR * (Twr4[:, 1:9, None] - T4)
        rfl = ecw[:, None] * sig * A_TB * ((self.Tfl + K)[:, None] ** 4 - T4[:, 0])
        rro = ecw[:, None] * sig * A_TB * ((self.Tro + K)[:, None] ** 4 - T4[:, -1])
        rl = ecw[:, None] * sig * A_SD * ((self.Twl[:, 1:9] + K) ** 4 - T4[:, :, 0])
        rrt = ecw[:, None] * sig * A_SD * ((self.Twrt[:, 1:9] + K) ** 4 - T4[:, :, -1])
        Qn += rf + rr; Qn[:, 0] += rfl; Qn[:, -1] += rro; Qn[:, :, 0] += rl; Qn[:, :, -1] += rrt
        Qrad += rf + rr; Qrad[:, 0] += rfl; Qrad[:, -1] += rro; Qrad[:, :, 0] += rl; Qrad[:, :, -1] += rrt
        Qw_f = -(rf.sum(-1)); Qw_r = -(rr.sum(-1)); Qw_l = -rl; Qw_rt = -rrt
        Qw_fl = -rfl.sum(-1); Qw_ro = -rro.sum(-1)
        # supports: module ends to side walls
        Gs = self.Gsup[:, None]
        sl = Gs * (self.Twl[:, 1:9] - Tc[:, :, 0]); sr = Gs * (self.Twrt[:, 1:9] - Tc[:, :, -1])
        Qn[:, :, 0] += sl; Qn[:, :, -1] += sr
        Qsup = xp.zeros_like(Tc); Qsup[:, :, 0] -= sl; Qsup[:, :, -1] -= sr     # + = out to supports
        Qw_l = Qw_l - sl; Qw_rt = Qw_rt - sr
        if self.o["G_hp"] > 0:      # heat pipes: each cell to the rear wall segment of its module level
            hp = self.o["G_hp"] * (self.Twr[:, 1:9, None] - Tc)
            Qn += hp; Qsup -= hp
            Qw_r = Qw_r - hp.sum(-1)
        Qair = xp.zeros_like(Tc)                    # convective heat cell -> air
        Tair_ref_acc = xp.zeros_like(Tc); Aexp = xp.zeros_like(Tc)
        rho_cp = P.RHO_AIR * P.CP_AIR
        hm = self.hm
        Qw_conv = dict(f=xp.zeros((B, NSEG)), r=xp.zeros((B, NSEG)), l=xp.zeros((B, NSEG)), rt=xp.zeros((B, NSEG)),
                       fl=xp.zeros(B), ro=xp.zeros(B))
        def Gface(h, A, Rint):
            return 1.0 / (1.0 / (h * A) + Rint)

        if self.forced:
            Qm = self.flow * (1 - self.fside)
            w = self.w
            # ---- channel 0 (bottom space): inlet air -> under M1 + floor + rear seg0 + side segs0
            W0 = rho_cp * Qm * w[:, 0]
            h0 = self.h_forced(Qm * w[:, 0], P.CAB_W * P.Z_BOTTOM, 2 * P.Z_BOTTOM, P.CAB_D, xp) * hm
            G = xp.concatenate([Gface(h0[:, None], A_TB, self.Rint_z[:, None]) * xp.ones((B, NC)),
                                (h0 * self.A_floor)[:, None], (h0 * self.Aw_rear[0])[:, None]], 1)
            Ts = xp.concatenate([Tc[:, 0], self.Tfl[:, None], self.Twr[:, 0:1]], 1)
            T_ch0, Qs, Tref = self.march(self.Tsup, W0, G, Ts, xp)
            Qair[:, 0] += Qs[:, :NC]; Tair_ref_acc[:, 0] += Tref[:, None] * A_TB; Aexp[:, 0] += A_TB
            Qw_conv["fl"] += Qs[:, NC]; Qw_conv["r"][:, 0] += Qs[:, NC + 1]
            # ---- front plenum, segments 1..9, branching channels 1..8
            Tf = self.Tsup.copy()
            Afp = P.CAB_W * P.Y0; Dfp = 2 * P.Y0 * P.CAB_W / (P.CAB_W + P.Y0)
            T_branch = [None] * 9
            frac_left = 1 - w[:, 0]
            for s in range(1, 10):
                Qs_flow = Qm * frac_left
                W = rho_cp * Qs_flow
                hf = self.h_forced(Qs_flow, Afp, Dfp, SEG_H[s], xp)
                Gw = (hf * hm * self.Aw_front[s])[:, None]
                if s <= 8:
                    m = s - 1
                    dTn = Tc[:, m] - Tf[:, None]
                    h = (hf[:, None] ** 3 + self.h_nat_v(dTn, P.CELL_Z, xp) ** 3) ** (1 / 3) * hm[:, None]
                    G = xp.concatenate([Gface(h, A_FR, self.Rint_y[:, None]), Gw], 1)
                    Ts = xp.concatenate([Tc[:, m], self.Twf[:, s:s + 1]], 1)
                    Tf_new, Qs, Tref = self.march(Tf, W, G, Ts, xp)
                    Qair[:, m] += Qs[:, :NC]; Tair_ref_acc[:, m] += Tref[:, None] * A_FR; Aexp[:, m] += A_FR
                    Qw_conv["f"][:, s] += Qs[:, NC]
                    Tf = Tf_new
                    T_branch[s] = Tf.copy()          # air entering channel j = s
                    if s <= 7:
                        frac_left = frac_left - w[:, s]   # the remainder (w8) rises to the top space
                else:
                    Tf_new, Qs, _ = self.march(Tf, W, Gw, self.Twf[:, 9:10], xp)
                    Qw_conv["f"][:, 9] += Qs[:, 0]; Tf = Tf_new
            # ---- channels 1..7 (gaps) per cell column, channel 8 over M8 top + roof
            Ach = P.MOD_LEN * P.GAP_Z
            T_ch_out = [T_ch0] + [None] * 8
            Qch_heat = [None] * 9
            for j in range(1, 9):
                Qj = Qm * w[:, j]
                Wcol = rho_cp * Qj / NC
                if j <= 7:
                    hj = self.h_forced(Qj, Ach, 2 * P.GAP_Z, P.CELL_Y, xp) * hm * self.hmg
                    Gc = Gface(hj[:, None], A_TB, self.Rint_z[:, None]) * xp.ones((B, NC))
                    G = xp.stack([Gc, Gc], -1)
                    Ts = xp.stack([Tc[:, j - 1], Tc[:, j]], -1)
                    # dead-air gap: the effective through-flow is the forced share plus buoyant/diffusive exchange
                    Wcol = Wcol + self.Gexf
                    To, Qs, Tref = self.march(T_branch[j][:, None], Wcol[:, None], G, Ts, xp)
                    Qair[:, j - 1] += Qs[..., 0]; Qair[:, j] += Qs[..., 1]
                    Tair_ref_acc[:, j - 1] += Tref * A_TB; Tair_ref_acc[:, j] += Tref * A_TB
                    Aexp[:, j - 1] += A_TB; Aexp[:, j] += A_TB
                    Qch_heat[j] = Qs.sum((1, 2))      # all gap heat ends up in the rear plenum stream
                else:
                    h8 = self.h_forced(Qj, P.CAB_W * P.TOP_SPACE, 2 * P.TOP_SPACE, P.CAB_D, xp) * hm
                    G = xp.concatenate([Gface(h8[:, None], A_TB, self.Rint_z[:, None]) * xp.ones((B, NC)),
                                        (h8 * self.A_roof)[:, None]], 1)
                    Ts = xp.concatenate([Tc[:, -1], self.Tro[:, None]], 1)
                    To, Qs, Tref = self.march(Tf, rho_cp * Qj, G, Ts, xp)
                    Qair[:, -1] += Qs[:, :NC]; Tair_ref_acc[:, -1] += Tref[:, None] * A_TB; Aexp[:, -1] += A_TB
                    Qw_conv["ro"] += Qs[:, NC]
                    T_ch_out[8] = To
            # ---- rear plenum
            Tr = T_ch0.copy(); flow_r = Qm * w[:, 0]
            for s in range(1, 10):
                if s <= 8:
                    if s >= 2:
                        j = s - 1
                        Qj = Qm * w[:, j]
                        Tr = (rho_cp * (Tr * flow_r + T_branch[j] * Qj) + Qch_heat[j]) / (rho_cp * (flow_r + Qj))
                        flow_r = flow_r + Qj
                    m = s - 1
                    W = rho_cp * flow_r
                    hf = self.h_forced(flow_r, Afp, Dfp, SEG_H[s], xp)
                    dTn = Tc[:, m] - Tr[:, None]
                    h = (hf[:, None] ** 3 + self.h_nat_v(dTn, P.CELL_Z, xp) ** 3) ** (1 / 3) * hm[:, None]
                    G = xp.concatenate([Gface(h, A_FR, self.Rint_y[:, None]), (hf * hm * self.Aw_rear[s])[:, None]], 1)
                    Ts = xp.concatenate([Tc[:, m], self.Twr[:, s:s + 1]], 1)
                    Tr, Qs, Tref = self.march(Tr, W, G, Ts, xp)
                    Qair[:, m] += Qs[:, :NC]; Tair_ref_acc[:, m] += Tref[:, None] * A_FR; Aexp[:, m] += A_FR
                    Qw_conv["r"][:, s] += Qs[:, NC]
                else:
                    Q8 = Qm * w[:, 8]
                    Tr = (Tr * flow_r + T_ch_out[8] * Q8) / (flow_r + Q8); flow_r = flow_r + Q8
                    Tr = Tr + self.Q_inv / (rho_cp * flow_r)        # inverter heat into top-space air
                    hf = self.h_forced(flow_r, Afp, Dfp, SEG_H[9], xp) * hm
                    Tr, Qs, _ = self.march(Tr, rho_cp * flow_r, (hf * self.Aw_rear[9])[:, None], self.Twr[:, 9:10], xp)
                    Qw_conv["r"][:, 9] += Qs[:, 0]
            # ---- side clearances (two streams), end-cell x faces + side walls + supports already done
            Qsd = self.flow * self.fside / 2
            Asd = P.X0 * P.CAB_D; Dsd = 2 * P.X0 * P.CAB_D / (P.X0 + P.CAB_D)
            Tout_sides = []
            for side, col, Tw, key in ((0, 0, self.Twl, "l"), (1, NC - 1, self.Twrt, "rt")):
                Ts_air = self.Tsup.copy()
                W = rho_cp * Qsd
                for s in range(NSEG):
                    hs = self.h_forced(Qsd, Asd, Dsd, SEG_H[s], xp)
                    Gw = (hs * hm * self.Aw_side[s])[:, None]
                    if 1 <= s <= 8:
                        m = s - 1
                        h = (hs ** 3 + self.h_nat_v(Tc[:, m, col] - Ts_air, P.CELL_Z, xp) ** 3) ** (1 / 3) * hm
                        Gcell = 1.0 / (1.0 / (h * A_SD) + self.Rint_x + self.rc / A_SD)
                        G = xp.stack([Gcell, Gw[:, 0]], -1)
                        Ts = xp.stack([Tc[:, m, col], Tw[:, s]], -1)
                        Ts_air, Qs, Tref = self.march(Ts_air, W, G, Ts, xp)
                        Qair[:, m, col] += Qs[:, 0]; Tair_ref_acc[:, m, col] += Tref * A_SD; Aexp[:, m, col] += A_SD
                        Qw_conv[key][:, s] += Qs[:, 1]
                    else:
                        Ts_air, Qs, _ = self.march(Ts_air, W, Gw, Tw[:, s:s + 1], xp)
                        Qw_conv[key][:, s] += Qs[:, 0]
                Tout_sides.append(Ts_air)
            T_out = (Tr * Qm + (Tout_sides[0] + Tout_sides[1]) * Qsd) / self.flow
            self.T_out = T_out
            self.E["enth"] += rho_cp * self.flow * (T_out - self.Tsup) * dt
        else:
            # ================= passive sealed cabinet: buoyant loop =================
            Qup = self.Qc
            Wpl = rho_cp * Qup * (1 - self.fside) / 2          # front and rear upflow streams
            Wsd = rho_cp * Qup * self.fside / 2
            # gap / bottom / top channel nodes: faces at h_gap_nat, exchange G_ex with plenums at that height
            # channel j touches top of module j-1 and bottom of module j (j=0: M1 bottom + floor, j=8: M8 top + roof)
            Qex_f = xp.zeros((B, NSEG)); Qex_r = xp.zeros((B, NSEG))
            Tpl_f_prev = getattr(self, "Tpl_f", None)
            Tpl_r_prev = getattr(self, "Tpl_r", None)
            if Tpl_f_prev is None:
                Tpl_f_prev = self.T_ret[:, None] * xp.ones((B, NSEG)); Tpl_r_prev = Tpl_f_prev.copy()
            hg = self.hgap * hm
            for j in range(9):
                Gl = []; Tl = []
                if j >= 1:
                    Gl.append(Gface(hg[:, None], A_TB, self.Rint_z[:, None]) * xp.ones((B, NC))); Tl.append(Tc[:, j - 1])
                if j <= 7:
                    Gl.append(Gface(hg[:, None], A_TB, self.Rint_z[:, None]) * xp.ones((B, NC))); Tl.append(Tc[:, j])
                Gc = xp.concatenate(Gl, 1); Tcs = xp.concatenate(Tl, 1)
                Gwall = (hg * (self.A_floor if j == 0 else self.A_roof if j == 8 else 0.0))
                Twall = self.Tfl if j == 0 else self.Tro if j == 8 else self.Tfl * 0
                s_f = 1 if j == 0 else (9 if j == 8 else j + 1)
                s_f = min(s_f, 9)
                Tp = 0.5 * (Tpl_f_prev[:, s_f] + Tpl_r_prev[:, s_f])
                Gx = self.Gex
                Tch = ((Gc * Tcs).sum(1) + Gwall * Twall + Gx * Tp) / (Gc.sum(1) + Gwall + Gx)
                Qs = Gc * (Tcs - Tch[:, None])
                k0 = 0
                if j >= 1:
                    Qair[:, j - 1] += Qs[:, :NC]; Tair_ref_acc[:, j - 1] += Tch[:, None] * A_TB; Aexp[:, j - 1] += A_TB; k0 = NC
                if j <= 7:
                    Qair[:, j] += Qs[:, k0:k0 + NC]; Tair_ref_acc[:, j] += Tch[:, None] * A_TB; Aexp[:, j] += A_TB
                if j == 0: Qw_conv["fl"] += Gwall * (Twall - Tch)
                if j == 8: Qw_conv["ro"] += Gwall * (Twall - Tch)
                qx = Gx * (Tch - Tp)
                Qex_f[:, s_f] += qx / 2; Qex_r[:, s_f] += qx / 2
            # upflow streams along cell front / rear faces (+ exchange sources)
            Tpl_f = xp.zeros((B, NSEG)); Tpl_r = xp.zeros((B, NSEG))
            Ttops = []
            for face, Wst, Tpl, Qex, Rint, key in (("f", Wpl, Tpl_f, Qex_f, self.Rint_y, "f"), ("r", Wpl, Tpl_r, Qex_r, self.Rint_y, "r")):
                Ta = self.T_ret.copy()
                for s in range(NSEG):
                    Ta = Ta + Qex[:, s] / Wst
                    if 1 <= s <= 8:
                        m = s - 1
                        h = self.h_nat_v(Tc[:, m] - Ta[:, None], P.CELL_Z, xp) * hm[:, None]
                        G = Gface(h, A_FR, Rint[:, None])
                        Ta_new, Qs, Tref = self.march(Ta, Wst, G, Tc[:, m], xp)
                        Qair[:, m] += Qs; Tair_ref_acc[:, m] += Tref[:, None] * A_FR; Aexp[:, m] += A_FR
                        Ta = Ta_new
                    Tpl[:, s] = Ta
                Ttops.append(Ta)
            self.Tpl_f, self.Tpl_r = Tpl_f, Tpl_r
            # side upflows along end-cell faces
            for col in (0, NC - 1):
                Ta = self.T_ret.copy()
                for s in range(1, 9):
                    m = s - 1
                    h = self.h_nat_v(Tc[:, m, col] - Ta, P.CELL_Z, xp) * hm
                    Gcell = 1.0 / (1.0 / (h * A_SD) + self.Rint_x + self.rc / A_SD)
                    Ta_new, Qs, Tref = self.march(Ta, Wsd, Gcell[:, None], Tc[:, m, col][:, None], xp)
                    Qair[:, m, col] += Qs[:, 0]; Tair_ref_acc[:, m, col] += Tref * A_SD; Aexp[:, m, col] += A_SD
                    Ta = Ta_new
                Ttops.append(Ta)
            Wtot = 2 * Wpl + 2 * Wsd
            T_top = (Ttops[0] * Wpl + Ttops[1] * Wpl + (Ttops[2] + Ttops[3]) * Wsd) / Wtot + self.Q_inv / Wtot
            # downflow along all walls, top segment to bottom
            Td = T_top
            for s in range(NSEG - 1, -1, -1):
                Ls = max(SEG_H[s], 0.15)
                Gl = []; Tl = []
                for Aw, Tw in ((self.Aw_front, self.Twf), (self.Aw_rear, self.Twr), (self.Aw_side, self.Twl), (self.Aw_side, self.Twrt)):
                    hw = self.h_nat_v(Tw[:, s] - Td, 2.35, xp) * hm
                    Gl.append(hw * Aw[s]); Tl.append(Tw[:, s])
                G = xp.stack(Gl, -1); Ts = xp.stack(Tl, -1)
                Td, Qs, _ = self.march(Td, Wtot, G, Ts, xp)
                Qw_conv["f"][:, s] += Qs[:, 0]; Qw_conv["r"][:, s] += Qs[:, 1]
                Qw_conv["l"][:, s] += Qs[:, 2]; Qw_conv["rt"][:, s] += Qs[:, 3]
            self.E["loop"] += Wtot * (Td - self.T_ret) * dt
            self.T_ret = Td
            self.T_out = T_top
        # ---------------- update cells ----------------
        Qn -= Qair
        self.E["gen"] += q.sum((1, 2)) * dt + self.Q_inv * dt
        C_eff = self.Ccell
        if self.o["pcm_kg"] > 0:    # phase-change plates: apparent capacity m*L/dT inside the melting band
            band = xp.abs(Tc - self.o["pcm_Tm"]) < self.o["pcm_dT"] / 2
            C_eff = self.Ccell + xp.where(band, self.o["pcm_kg"] * self.o["pcm_L"] / self.o["pcm_dT"], 0.0) \
                    + self.o["pcm_kg"] * 2000.0          # sensible cp of the PCM, ~2 kJ/kg K
        dTc = Qn * dt / C_eff
        # ---------------- walls: radiation in, convection out, external ----------------
        ext = lambda Tw, A: self.hext[:, None] * A * (Tw - self.Tamb[:, None])
        t = self.t
        sol_roof = self.o["solar_roof"](t) if callable(self.o["solar_roof"]) else self.o["solar_roof"]
        sol_side = self.o["solar_side"](t) if callable(self.o["solar_side"]) else self.o["solar_side"]
        def wall_update(Tw, C, Qrad_in, Qconv_out, A, Qsol=0.0):
            Qe = self.hext[:, None] * A * (Tw - self.Tamb[:, None])
            return Tw + (Qrad_in - Qconv_out - Qe + Qsol) * dt / C, Qe
        Qw_f_full = xp.zeros((B, NSEG)); Qw_f_full[:, 1:9] = Qw_f
        Qw_r_full = xp.zeros((B, NSEG)); Qw_r_full[:, 1:9] = Qw_r
        Qw_l_full = xp.zeros((B, NSEG)); Qw_l_full[:, 1:9] = Qw_l.sum(-1) if Qw_l.ndim == 3 else Qw_l
        Qw_rt_full = xp.zeros((B, NSEG)); Qw_rt_full[:, 1:9] = Qw_rt.sum(-1) if Qw_rt.ndim == 3 else Qw_rt
        Af, Ar, As_ = self.Aw_front_x, self.Aw_rear_x, self.Aw_side_x
        # NOTE: Qw_conv holds heat INTO AIR from the wall (positive = wall loses heat)
        Twf, e1 = wall_update(self.Twf, self.Cw_front, Qw_f_full, Qw_conv["f"], Af)
        Twr, e2 = wall_update(self.Twr, self.Cw_rear, Qw_r_full, Qw_conv["r"], Ar)
        Twl, e3 = wall_update(self.Twl, self.Cw_side, Qw_l_full, Qw_conv["l"], As_)
        sm = self.sol_mult
        Twrt, e4 = wall_update(self.Twrt, self.Cw_side, Qw_rt_full, Qw_conv["rt"], As_, (sm * sol_side)[:, None] * As_)
        Qe_fl = self.hext * self.A_floor * (self.Tfl - self.Tamb)
        Qe_ro = self.hext * self.A_roof * (self.Tro - self.Tamb)
        Tfl = self.Tfl + (Qw_fl - Qw_conv["fl"] - Qe_fl) * dt / self.Cw_floor
        Tro = self.Tro + (Qw_ro - Qw_conv["ro"] - Qe_ro + sm * sol_roof * self.A_roof) * dt / self.Cw_roof
        Esol = sm * (sol_roof * self.A_roof + sol_side * float(As_.sum())) * dt
        self.E["gen"] += Esol
        self.E["ext"] += (e1.sum(1) + e2.sum(1) + e3.sum(1) + e4.sum(1) + Qe_fl + Qe_ro) * dt
        # stored-energy increments
        self.E["store"] += (dTc * C_eff).sum((1, 2)) + ((Twf - self.Twf) * self.Cw_front).sum(1) \
            + ((Twr - self.Twr) * self.Cw_rear).sum(1) + ((Twl - self.Twl) * self.Cw_side).sum(1) \
            + ((Twrt - self.Twrt) * self.Cw_side).sum(1) + (Tfl - self.Tfl) * self.Cw_floor + (Tro - self.Tro) * self.Cw_roof
        if record:
            Qface = Qair + (-Qrad)   # heat leaving through faces (conv + rad); used for surface T
            Tsurf = Tc - Qface * (self.Rint_y[:, None, None] * 0.5 + self.Rint_z[:, None, None] * 0.5)
            qv = q / P.CELL_VOL
            dTgen = qv / (6 * (self.kin[:, None, None] / LZH ** 2 + self.kin[:, None, None] / LYH ** 2))
            # interior max: generation bump above the mean + through-flow bump when heat crosses the cell in x
            Tint = Tc + dTgen + xp.abs(Qnb) * (LXH / (self.kx[:, None, None] * A_SD)) * self.o["tint_gamma"]
            self.rec = dict(Tmean=Tc.copy(), Tmax=Tint, Tsurf=Tsurf,
                            Tair=xp.where(Aexp > 0, Tair_ref_acc / xp.maximum(Aexp, 1e-12), xp.nan),
                            q=q, Qair=Qair, Qnb=-Qnb, Qsup=Qsup, Qrad_out=-Qrad)
        self.Tc = Tc + dTc
        self.Twf, self.Twr, self.Twl, self.Twrt, self.Tfl, self.Tro = Twf, Twr, Twl, Twrt, Tfl, Tro
        self.t += dt

    def energy_error(self):
        E = self.E
        out = E["store"] + E["ext"] + E["enth"] + E["loop"]
        return (E["gen"] - out) / self.xp.maximum(E["gen"], 1e-9)
