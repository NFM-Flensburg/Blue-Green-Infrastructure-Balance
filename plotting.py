import os
import pandas as pd
import plotly
import plotly.graph_objects as go


def waterfall(df, output_dir):
    df = df[df["BFF_Area"] != 0]

    # --- Create label "Before → After" ---
    df["Transition"] = df["Before"] + " → " + df["After"]

    # --- Sort by BFF_Area ---
    df = df.sort_values(by="BFF_Area", ascending=False).reset_index(drop=True)

    # --- Compute Net-BGI Balance ---
    net_balance = df["BFF_Area"].sum()

    # --- Append total bar for Net-BGI Balance ---
    df_total = pd.DataFrame({
        "Transition": ["Net-BGI Balance"],
        "BFF_Area": [net_balance]
    })

    df_final = pd.concat([df, df_total], ignore_index=True)
    # --- Plotly Waterfall ---
    fig = go.Figure(go.Waterfall(
        name="BFF_Area",
        orientation="v",
        x=df_final["Transition"],
        y=df_final["BFF_Area"],
        measure = ["relativ"] * (len(df_final)-1) + ["total"],
        connector={"line": {"color": "black", "width": 1, "dash": "dot"}},
        decreasing={"marker": {"color": "#CDDBA9"}},  # red
        increasing={"marker": {"color": "#BF5743"}},  # green
        totals={"marker": {"color": "#79B2D1"}},  # blue
        text=[f"{v:.1f}" for v in df_final["BFF_Area"]],
        textposition="outside"
    ))


    # --- Layout ---
    fig.update_layout(
        title="Blue-Green-Infrastructure Balance",
        xaxis_title="Transition (Before → After)",
        yaxis_title="Area",
        showlegend=False,
        xaxis=dict(tickangle=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13),
        margin=dict(l=60, r=40, t=80, b=80)
    )
    print("Plotting Waterfall Diagramm.")
    plotly.offline.plot(fig, filename=os.path.join(output_dir, 'interactive_waterfall_plot.html'), auto_open=False)
