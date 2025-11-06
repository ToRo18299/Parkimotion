import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# === Configuración ===
carpeta_csv = r"C:\Users\DIEGO RAMOS\modelado_planta_vib\interfazdash\data"
carpeta_salida = os.path.join(carpeta_csv, "..", "graficas")
os.makedirs(carpeta_salida, exist_ok=True)

# === Unir todos los CSV de la carpeta ===
csvs = [os.path.join(carpeta_csv, f) for f in os.listdir(carpeta_csv) if f.endswith(".csv")]
df_total = pd.concat([pd.read_csv(f) for f in csvs], ignore_index=True)
df_total.columns = [col.strip() for col in df_total.columns]

# === Calcular error de frecuencia
df_total["Error (Hz)"] = (df_total["Frecuencia deseada"] - df_total["Frecuencia detectada"]).abs().round(3)

# === Asignar frecuencia esperada por tipo de paciente
frecuencias_referencia = {
    "leve": 3.0,
    "moderado": 5.0,
    "severo": 7.0
}
df_total["Frecuencia deseada esperada (Hz)"] = df_total["Paciente"].map(frecuencias_referencia)

# === Seleccionar muestras balanceadas (n = 217 por grupo)
n_muestras = 217
df_balanceado = pd.concat([
    df_total[df_total["Paciente"] == "leve"].sample(n=n_muestras, random_state=42),
    df_total[df_total["Paciente"] == "moderado"].sample(n=n_muestras, random_state=42),
    df_total[df_total["Paciente"] == "severo"].sample(n=n_muestras, random_state=42)
], ignore_index=True)

# === Tabla 1: Medidas observadas
tabla1 = df_balanceado.groupby("Paciente").agg({
    "Frecuencia deseada esperada (Hz)": "first",
    "Frecuencia detectada": "mean",
    "Amplitud pico (g)": "mean"
}).round(3).reset_index()

tabla1.columns = [
    "Paciente", "Frecuencia deseada (Hz)",
    "Frecuencia detectada promedio (Hz)", "Amplitud pico promedio (g)"
]

# === Guardar tabla 1 como imagen
fig, ax = plt.subplots(figsize=(10, 2))
ax.axis("off")
tabla = ax.table(cellText=tabla1.values,
                 colLabels=tabla1.columns,
                 cellLoc='center',
                 loc='center')
tabla.scale(1.2, 1.5)
plt.title("Medidas observadas por tipo de paciente", pad=20)
plt.savefig(os.path.join(carpeta_salida, "tabla_medidas_observadas.png"), bbox_inches="tight", dpi=200)
plt.close()

# === Guardar tabla 1 como Excel
tabla1.to_excel(os.path.join(carpeta_salida, "tabla_medidas_observadas.xlsx"), index=False)

# === Tabla 2: Resumen de errores y amplitudes
resumen_total = df_balanceado.groupby("Paciente").agg({
    "Error (Hz)": ["mean", "std", "max"],
    "Amplitud pico (g)": "mean",
    "Amplitud estimada (cm)": "mean"
}).round(3).reset_index()

resumen_total.columns = [
    "Paciente", "Error Medio (Hz)", "Desviación Std (Hz)", "Error Máximo (Hz)",
    "Amplitud Media (g)", "Desplazamiento Medio (cm)"
]

resumen_total["Frecuencia deseada esperada (Hz)"] = resumen_total["Paciente"].map(frecuencias_referencia)
resumen_total = resumen_total[[ 
    "Paciente", "Frecuencia deseada esperada (Hz)",
    "Error Medio (Hz)", "Desviación Std (Hz)", "Error Máximo (Hz)",
    "Amplitud Media (g)", "Desplazamiento Medio (cm)"
]]

# === Guardar tabla 2 como imagen
fig, ax = plt.subplots(figsize=(10, 2.5))
ax.axis("off")
tabla = ax.table(cellText=resumen_total.values,
                 colLabels=resumen_total.columns,
                 cellLoc='center',
                 loc='center')
tabla.scale(1.2, 1.5)
plt.title("Resumen de errores y amplitudes por tipo de paciente", pad=20)
plt.savefig(os.path.join(carpeta_salida, "tabla_resumen_errores.png"), bbox_inches="tight", dpi=200)
plt.close()

# === Guardar tabla 2 como Excel
resumen_total.to_excel(os.path.join(carpeta_salida, "tabla_resumen_errores.xlsx"), index=False)

# === Gráfico de barras: Error medio por paciente
resumen_error = df_balanceado.groupby("Paciente")["Error (Hz)"].mean().round(3).reset_index()
plt.figure(figsize=(6, 4))
sns.barplot(data=resumen_error, x="Paciente", y="Error (Hz)", palette="viridis")
plt.title("Error medio por tipo de paciente")
plt.ylabel("Error absoluto (Hz)")
plt.xlabel("Paciente")
plt.tight_layout()
plt.savefig(os.path.join(carpeta_salida, "error_medio_barra.png"), dpi=200)
plt.close()

print("✅ Análisis completo (sin prueba T). Las tablas y gráficos fueron guardados en la carpeta 'graficas/'")
