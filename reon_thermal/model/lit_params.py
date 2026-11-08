"""Literature-based electrical parameters for a layered-oxide / hard-carbon sodium-ion cell (class LIT in the register).

OCV(SOC) and the SOC shape of the resistance are digitised from:
  M. Fronc, B. Stefanczak, "Experimental identification of the equivalent parameters of a sodium-ion cell",
  Przeglad Elektrotechniczny 101(8) (2025) 174-180 - commercial 18650 Na-ion, 1300 mAh, 3.1 V nominal, 1.5-3.95 V,
  <20 mOhm (Table 3); Fig. 10 OCV-SOC (HPPC + relaxed voltage), Fig. 11 series resistance, Fig. 12 dynamic resistance.
  Read off the published figures by eye (+/- 0.03 V, +/- 0.3 mOhm).
Temperature dependence of the polarisation resistance:
  Leeds group, "early-generation 18650 Na-ion cells ...", Applied Energy (2026), doi:10.1016/j.apenergy.2026.127687 (CC BY 4.0):
  EIS polarisation resistance is Arrhenius with Ea ~ 70-75 kJ/mol for layered oxides (NFM, CFM); NFPP less sensitive.
Ohmic-part activation energy 15 kJ/mol and the ohmic/polarisation split at the 2 h time scale are ANALYST-ASSUMED.
No tabulated Na-ion entropic coefficient was found (only figures: Zhang et al., J. Electrochem. Soc. 170 (2023)
070514-type study of NCFMO/HC, doi:10.1149/1945-7111/ace5e5; Mercer et al., ChemPhysChem 2022) -> dU/dT is a
sensitivity (0, +/-0.2 mV/K).
Absolute resistance: the 18650's ~20 mOhm scaled by capacity gives ~0.17 mOhm for a 150 Ah cell (10 s pulse, ~1 W at
0.5 C); PyBaMM Chayambuka2022 gives ~11 % loss (28 W). REF_MODE "brief" scales R so the mean heat over a 30 kW, 2 h
discharge at 25 C equals the brief's 6.1 W; "pulse18650" uses the scaled pulse resistance as published.
"""
import numpy as np
SOC_PTS = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100], float) / 100
OCV_PTS = np.array([1.86, 2.31, 2.62, 2.80, 2.875, 3.01, 3.18, 3.35, 3.54, 3.67, 3.83])          # V, Fronc 2025 Fig. 10
R0_PTS = np.array([20.0, 19.7, 19.75, 18.95, 19.8, 19.9, 18.8, 19.0, 18.8, 18.7, 18.7])          # mOhm, Fig. 11 (HPPC)
R1_PTS = np.array([7.8, 7.8, 2.2, 0.7, 0.95, 0.7, 0.8, 0.9, 1.2, 0.8, 4.3])                      # mOhm, Fig. 12 (10 % value held at 0 %)
CAP_18650_AH = 1.3
EA_POL = 72e3       # J/mol, Leeds 2026 (70-75 kJ/mol, layered oxides)
EA_OHM = 15e3       # J/mol, AA (electrolyte conductivity)
W_POL = 0.5         # AA: share of the 2 h-discharge resistance that behaves like polarisation (pulse data say ~0.05; diffusion adds more)
V_MIN, V_MAX = 1.5, 3.95                                                                        # V, Fronc 2025 Table 3
MEAN_OCV = float(np.trapezoid(OCV_PTS, SOC_PTS))                                                 # ~3.02 V

def ocv(soc):
    return np.interp(np.clip(soc, 0, 1), SOC_PTS, OCV_PTS)

def r_shape(soc):
    """total-resistance SOC shape, normalised to 1 at 50 % SOC"""
    tot = R0_PTS + R1_PTS
    return np.interp(np.clip(soc, 0, 1), SOC_PTS, tot) / np.interp(0.5, SOC_PTS, tot)

def r_temp(T_C, ea_pol=EA_POL, ea_ohm=EA_OHM, w_pol=W_POL, T_ref=25.0):
    Rg = 8.314; x = 1 / (np.asarray(T_C) + 273.15) - 1 / (T_ref + 273.15)
    return (1 - w_pol) * np.exp(ea_ohm / Rg * x) + w_pol * np.exp(ea_pol / Rg * x)

R_PULSE_150AH = float(np.interp(0.5, SOC_PTS, R0_PTS + R1_PTS)) * 1e-3 * CAP_18650_AH / 150.0     # Ohm
