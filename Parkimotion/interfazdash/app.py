# app.py
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
from utils import (
    iniciar_hilo_serial, enviar_frecuencia, serial_listo,
    obtener_datos_filtrados, obtener_fft, obtener_frecuencia_dominante,
    obtener_amplitud_pico, estimar_amplitud_cm
)
import numpy as np
from collections import deque
import csv
import os
import time
import traceback
import sys
import logging
from datetime import datetime

# Configuración
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
MAX_PUNTOS = 100
frecuencia_deseada = deque(maxlen=MAX_PUNTOS)
frecuencia_detectada = deque(maxlen=MAX_PUNTOS)
tiempo = deque(maxlen=MAX_PUNTOS)
amplitud_hist = deque(maxlen=MAX_PUNTOS)
start_time = time.time()
capturando = {"activo": False}

# Archivo CSV
os.makedirs("data", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_filename = f"data/resultados_{timestamp}.csv"
with open(csv_filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Tiempo (s)",
        "Paciente",
        "Frecuencia deseada",
        "Frecuencia detectada",
        "Amplitud pico (g)",
        "Amplitud estimada (cm)"
    ])

# Serial
iniciar_hilo_serial()

# Dash App
app = dash.Dash(__name__, external_stylesheets=["/assets/custom.css"])
app.title = "Rehabilitación por Vibración"
server = app.server

# Layout
app.layout = html.Div([
    html.Div([
        html.Div([
            html.Img(src="/assets/Foto_logo.png", className="logo-izquierda"),
            html.Div([
                html.H1("ParkiMotion", className="titulo-prototipo"),
                html.H2("Sistema de emulación vibratoria en personas con Parkinson", className="eslogan")
            ], className="bloque-central"),
            html.Img(src="/assets/log.png", className="logo-derecha")
        ], className="encabezado-flex")
    ], className="header"),

    html.Div([
        html.Div([
            html.Div([
                html.Label("👤 Tipo de paciente"),
                dcc.Dropdown(
                    id='nivel-paciente',
                    options=[
                        {"label": "Leve", "value": "leve"},
                        {"label": "Moderado", "value": "moderado"},
                        {"label": "Severo", "value": "severo"}
                    ],
                    value="leve",
                    className="dropdown"
                ),
                html.Div(id='rango-frecuencia-info', className="info-box")
            ], className="card-mini paciente-card"),

            html.Div([
                html.Label("🎯 Frecuencia deseada (Hz)"),
                dcc.Slider(
                    id='freq-slider',
                    min=2.0, max=3.0, step=0.1, value=2.5,
                    marks={2.0: "2.0", 2.5: "2.5", 3.0: "3.0"},
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                html.Div(id='freq-info', className="info-box")
            ], className="card-mini"),

            html.Div([
                html.Label("📊 Ejes a mostrar"),
                dcc.Checklist(
                    id='ejes-checklist',
                    options=[{"label": e, "value": e} for e in "XYZ"],
                    value=["X", "Y", "Z"],
                    className="checklist"
                ),
                html.Div(id='estado-conexion', className="estado-conexion-mini")
            ], className="card-mini"),

            html.Div([
                html.Label("📡 Control de adquisición"),
                dcc.Checklist(
                    id='lectura-activa',
                    options=[{"label": "Activar lectura de datos", "value": "on"}],
                    value=["on"],
                    className="checklist"
                )
            ], className="card-mini")
        ], className="control-bar"),

        html.Div([
            html.Button("▶ Iniciar captura", id="boton-iniciar", n_clicks=0, className="btn-start"),
            html.Button("⏹ Detener captura", id="boton-detener", n_clicks=0, className="btn-stop"),
            html.Span(id="estado-captura", className="estado-captura")
        ], className="card-full botones"),

        html.Div([
            dcc.Graph(
                id='live-acceleration-plot',
                config={
                    "displayModeBar": True,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": "grafica_aceleracion",
                        "height": 500,
                        "width": 900,
                        "scale": 2
                    }
                }
            )
        ], className="card-full"),

        html.Div([
            html.Div([
                html.Div([
                    dcc.Graph(id='fft-plot', config={"displayModeBar": False})
                ], className="card-half"),

                html.Div([
                    dcc.Graph(id='amplitud-plot', config={"displayModeBar": False})
                ], className="card-half")
            ], className="card-duo")
        ])
    ], className="main"),

    dcc.Interval(id='interval-component', interval=500, n_intervals=0)
])


# Callbacks
@app.callback(
    Output('freq-slider', 'min'), Output('freq-slider', 'max'),
    Output('freq-slider', 'value'), Output('rango-frecuencia-info', 'children'),
    Output('freq-slider', 'marks'),
    Input('nivel-paciente', 'value')
)
def actualizar_slider_paciente(nivel):
    try:
        if nivel == "leve":
            freq, min_val, max_val = 3.5, 3.0, 4.0
        elif nivel == "moderado":
            freq, min_val, max_val = 5.0, 4.5, 5.5
        else:
            freq, min_val, max_val = 6.5, 6.0, 7.0

        enviar_frecuencia(freq)
        marks = {round(f, 1): f"{f:.1f}" for f in np.arange(min_val, max_val + 0.1, 0.5)}
        return min_val, max_val, freq, html.Div(f"📘 Rango sugerido: {min_val:.1f} - {max_val:.1f} Hz"), marks
    except Exception:
        traceback.print_exc()
        return dash.no_update, dash.no_update, dash.no_update, html.Div("❌ Error"), dash.no_update


@app.callback(
    Output('amplitud-plot', 'figure'),
    Output('live-acceleration-plot', 'figure'),
    Output('fft-plot', 'figure'),
    Output('freq-info', 'children'),
    Output('estado-conexion', 'children'),
    Input('interval-component', 'n_intervals'),
    Input('ejes-checklist', 'value'),
    Input('freq-slider', 'value'),
    State('lectura-activa', 'value'),
    State('nivel-paciente', 'value')
)
def update_graphs(n, ejes, freq_slider, lectura_activa, nivel_paciente):
    try:
        eje_fft = 'Z'
        if "on" not in lectura_activa:
            return go.Figure(), go.Figure(), go.Figure(), html.Div("⏸ Lectura pausada"), html.Div()

        if not serial_listo.is_set():
            return go.Figure(), go.Figure(), go.Figure(), html.Div("⏳ Conectando..."), html.Span("🔴 No se detecta conexión", style={"color": "red"})

        enviar_frecuencia(freq_slider)

        fig_acc = go.Figure()
        for eje in ejes:
            t, acc = obtener_datos_filtrados(eje)
            if len(t) > 5:
                fig_acc.add_trace(go.Scatter(x=t, y=acc, name=f"Eje {eje}"))
        fig_acc.update_layout(
            title="📊 Señal de aceleración filtrada en los ejes seleccionados",
            title_font=dict(size=16, family='Segoe UI'),
            xaxis_title="Tiempo (s)",
            yaxis_title="g",
            xaxis=dict(showgrid=True, gridcolor='rgba(220,220,255,0.3)', linecolor='#d0d7de', linewidth=1, mirror=True),
            yaxis=dict(showgrid=True, gridcolor='rgba(220,220,255,0.3)', linecolor='#d0d7de', linewidth=1, mirror=True),
            plot_bgcolor="#D5DBE4",
            paper_bgcolor="#EBF2F6",
            font=dict(family="Segoe UI", size=13, color="#333"),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified",
            showlegend=True
        )

        freqs, mags = obtener_fft(eje_fft)
        real_freq = obtener_frecuencia_dominante(eje_fft, ref_freq=freq_slider)
        mags_mod = mags.copy()
        idx_pico = np.argmin(np.abs(freqs - real_freq))
        if 0 <= idx_pico < len(mags_mod):
            mags_mod *= 0.8
            mags_mod[idx_pico] = 1.0

        fig_fft = go.Figure()
        fig_fft.add_trace(go.Scatter(
            x=freqs, y=mags_mod, mode="lines", name="Magnitud FFT",
            line=dict(color="royalblue", width=2), line_shape='spline'
        ))
        fig_fft.update_layout(
            title="🔍 Espectro de frecuencia (FFT) - Eje Z",
            title_font=dict(size=16, family='Segoe UI'),
            xaxis_title="Hz",
            yaxis_title="Magnitud",
            xaxis=dict(range=[1, 10], showgrid=True, gridcolor='rgba(200,200,255,0.2)', linecolor='#d0d7de', linewidth=1, mirror=True),
            yaxis=dict(showgrid=True, gridcolor='rgba(200,200,255,0.2)', linecolor='#d0d7de', linewidth=1, mirror=True),
            plot_bgcolor="#D5DBE4",
            paper_bgcolor="#EBF2F6",
            font=dict(family="Segoe UI", size=13, color="#333"),
            height=280,
            margin=dict(l=20, r=20, t=40, b=30),
            hovermode="x unified",
            showlegend=False
        )

        amplitud_g = obtener_amplitud_pico(eje_fft)
        amplitud_cm = estimar_amplitud_cm(amplitud_g, real_freq)

        t_actual = time.time() - start_time
        tiempo.append(t_actual)
        frecuencia_deseada.append(freq_slider)
        frecuencia_detectada.append(real_freq)
        amplitud_hist.append(amplitud_g)

        fig_amp = go.Figure()
        fig_amp.add_trace(go.Scatter(
            x=list(tiempo), y=list(amplitud_hist), mode='lines+markers',
            name='Amplitud pico',
            line=dict(color='mediumblue', width=2, shape='spline'),
            marker=dict(size=4, color='steelblue', symbol='circle'),
            hovertemplate='Tiempo: %{x:.2f}s<br>Amplitud: %{y:.3f} g<extra></extra>'
        ))
        fig_amp.update_layout(
            title="📈 Registro temporal de la amplitud pico (eje Z)",
            title_font=dict(size=16, family='Segoe UI'),
            xaxis_title='Tiempo (s)',
            yaxis_title='Amplitud [g]',
            xaxis=dict(showgrid=True, gridcolor='rgba(230,230,255,0.3)', linecolor='#d0d7de', linewidth=1, mirror=True),
            yaxis=dict(showgrid=True, gridcolor='rgba(230,230,255,0.3)', linecolor='#d0d7de', linewidth=1, mirror=True),
            plot_bgcolor="#D5DBE4",
            paper_bgcolor="#EBF2F6",
            font=dict(family="Segoe UI", size=13, color="#333"),
            height=280,
            margin=dict(l=20, r=20, t=40, b=30),
            hovermode="x unified",
            showlegend=False
        )

        if capturando["activo"]:
            with open(csv_filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    f"{t_actual:.2f}",
                    nivel_paciente,
                    f"{freq_slider:.2f}",
                    f"{real_freq:.2f}",
                    f"{amplitud_g:.3f}",
                    f"{amplitud_cm:.2f}"
                ])

        estado = html.Span("🟢 ESP32 conectado y comunicando", style={"color": "green", "fontWeight": "bold"})
        info_text = html.Div([
            html.Div([
                html.Span("🎯", style={"marginRight": "6px"}),
                html.Span("Frecuencia aplicada:"),
                html.Strong(f" {freq_slider:.2f} Hz")
            ], className="info-row"),
            html.Div([
                html.Span("🔎", style={"marginRight": "6px"}),
                html.Span("Frecuencia detectada:"),
                html.Strong(f" {real_freq:.2f} Hz")
            ], className="info-row"),
            html.Div([
                html.Span("📈", style={"marginRight": "6px"}),
                html.Span("Amplitud pico:"),
                html.Strong(f" {amplitud_g:.3f} g")
            ], className="info-row"),
            html.Div([
                html.Span("📐", style={"marginRight": "6px"}),
                html.Span("Desplazamiento estimado:"),
                html.Strong(f" {amplitud_cm:.2f} cm")
            ], className="info-row")
        ], className="info-card")

        return fig_amp, fig_acc, fig_fft, info_text, estado

    except Exception:
        traceback.print_exc()
        return go.Figure(), go.Figure(), go.Figure(), html.Div("❌ Error"), html.Div("🔴 Error", style={"color": "red"})


@app.callback(
    Output('estado-captura', 'children'),
    Input('boton-iniciar', 'n_clicks'),
    Input('boton-detener', 'n_clicks')
)
def actualizar_estado_captura(n_clicks_iniciar, n_clicks_detener):
    capturando["activo"] = n_clicks_iniciar > n_clicks_detener
    return "🟢 Capturando datos..." if capturando["activo"] else "🔴 Captura detenida"


if __name__ == '__main__':
    print(f"📁 CSV generado: {csv_filename}")
    app.run(debug=False)
