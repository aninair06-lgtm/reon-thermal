"""CoolProp: air properties at operating temperatures and an R-32 vapour-compression COP for the air-conditioning
comparison. pvlib: clear-sky irradiance (Ineichen) on a horizontal roof and a west-facing wall at a hot site
(Phoenix, AZ, 21 June), used as the solar load in the network instead of the sine approximation."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import CoolProp.CoolProp as CP
import pandas as pd, pvlib
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
out = {}
# ---- air properties
props = {}
for T in (20, 25, 40, 50, 60):
    Tk = T + 273.15
    props[str(T)] = dict(rho=CP.PropsSI("D", "T", Tk, "P", 101325, "Air"), cp=CP.PropsSI("C", "T", Tk, "P", 101325, "Air"),
                         k=CP.PropsSI("L", "T", Tk, "P", 101325, "Air"), mu=CP.PropsSI("V", "T", Tk, "P", 101325, "Air"),
                         Pr=CP.PropsSI("Prandtl", "T", Tk, "P", 101325, "Air"))
out["air"] = props
# ---- R-32 cycle COP: evaporator 10 C, condenser = ambient + 15 K, superheat 5 K, subcool 3 K, isentropic efficiency 0.7
def cop(T_amb, T_evap=10.0, eta=0.7, fluid="R32"):
    Te, Tc = T_evap + 273.15, T_amb + 15 + 273.15
    pe, pc = CP.PropsSI("P", "T", Te, "Q", 1, fluid), CP.PropsSI("P", "T", Tc, "Q", 1, fluid)
    h1 = CP.PropsSI("H", "T", Te + 5, "P", pe, fluid); s1 = CP.PropsSI("S", "T", Te + 5, "P", pe, fluid)
    h2s = CP.PropsSI("H", "S", s1, "P", pc, fluid); h2 = h1 + (h2s - h1) / eta
    h3 = CP.PropsSI("H", "T", Tc - 3, "P", pc, fluid)
    return (h1 - h3) / (h2 - h1)
out["ac_cop_R32"] = {str(T): cop(T) for T in (25, 30, 35, 40, 45)}
# ---- pvlib clear sky, Phoenix, 21 June
site = pvlib.location.Location(33.45, -112.07, tz="America/Phoenix", altitude=331)
times = pd.date_range("2026-06-21 00:00", "2026-06-21 23:59", freq="5min", tz=site.tz)
cs = site.get_clearsky(times, model="ineichen")
sp = site.get_solarposition(times)
roof = pvlib.irradiance.get_total_irradiance(0, 180, sp["apparent_zenith"], sp["azimuth"], cs["dni"], cs["ghi"], cs["dhi"])["poa_global"]
west = pvlib.irradiance.get_total_irradiance(90, 270, sp["apparent_zenith"], sp["azimuth"], cs["dni"], cs["ghi"], cs["dhi"])["poa_global"]
hours = (times.hour + times.minute / 60).values
out["solar"] = dict(site="Phoenix AZ, 2026-06-21, Ineichen clear sky", roof_peak_W_m2=float(roof.max()), west_peak_W_m2=float(west.max()),
                    roof_daily_kWh_m2=float(roof.sum() * 5 / 60 / 1000), west_daily_kWh_m2=float(west.sum() * 5 / 60 / 1000),
                    hours=hours.tolist(), roof=roof.round(1).tolist(), west=west.round(1).tolist())
json.dump(out, open(os.path.join(R, "coolprop_pvlib.json"), "w"), indent=1)
print("air 25 C", {k: round(v, 5) for k, v in props["25"].items()}, "\nair 50 C", {k: round(v, 5) for k, v in props["50"].items()})
print("R-32 COP:", {k: round(v, 2) for k, v in out["ac_cop_R32"].items()})
print("pvlib: roof peak %.0f W/m2, west peak %.0f W/m2, roof %.1f kWh/m2/day, west %.1f kWh/m2/day" % (roof.max(), west.max(), out["solar"]["roof_daily_kWh_m2"], out["solar"]["west_daily_kWh_m2"]))
