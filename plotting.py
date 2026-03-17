import os
import pandas as pd
import plotly
import plotly.graph_objects as go


def waterfall(df, project_title, output_dir):
    df = df[df["BFF_Area"] != 0].copy()

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

    total_color = "#5ECBC8" if net_balance >= 0 else "#CD4C46"
    total_idx = len(df_final) - 1

    # --- Plotly Waterfall ---
    fig = go.Figure(go.Waterfall(
        name="BFF_Area",
        orientation="v",
        x=df_final["Transition"],
        y=df_final["BFF_Area"],
        measure=["relative"] * (len(df_final) - 1) + ["total"],
        connector={"line": {"color": "black", "width": 1, "dash": "dot"}},
        decreasing={"marker": {"color": "#ECC846"}},
        increasing={"marker": {"color": "#4A588A"}},
        totals={"marker": {"color": total_color}},
        text=[f"{v:.1f}" for v in df_final["BFF_Area"]],
        textposition="outside",
        hovertemplate="Transition: %{x}<br>Area: %{y:.1f}<extra></extra>"
    ))

    # --- Zero line ---
    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(df_final) - 0.5,
        y0=0,
        y1=0,
        line=dict(color="black", width=1, dash="dash")
    )

    # --- Vertical separator before total bar ---
    fig.add_shape(
        type="line",
        x0=total_idx - 0.5,
        x1=total_idx - 0.5,
        y0=min(df_final["BFF_Area"].min(), net_balance) * 1.15,
        y1=max(df_final["BFF_Area"].max(), net_balance) * 1.15,
        line=dict(color="black", width=1.5, dash="dot")
    )

    # --- Optional subtle background for total area ---
    fig.add_vrect(
        x0=total_idx - 0.5,
        x1=total_idx + 0.5,
        fillcolor="lightgrey",
        opacity=0.08,
        line_width=0
    )

    # --- Annotation above total bar ---
    fig.add_annotation(
        x=total_idx,
        y=net_balance,
        text="Final Balance",
        showarrow=False,
        yshift=25 if net_balance >= 0 else -25,
        font=dict(size=12, color="black")
    )

    # --- Layout ---
    fig.update_layout(
        title="Blue-Green-Infrastructure Balance " + project_title,
        xaxis_title="Transition (Before → After)",
        yaxis_title="Area",
        showlegend=False,
        xaxis=dict(tickangle=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13),
        margin=dict(l=60, r=40, t=80, b=80)
    )

    print("Plotting Waterfall Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, "waterfall_plot.html"),
        auto_open=False
    )


def waterfall_short(df, project_title, output_dir):

    df = df[df["BFF_Area"] != 0]

    # --- Split positive and negative ---
    positive = df[df["BFF_Area"] > 0]["BFF_Area"].sum()
    negative = df[df["BFF_Area"] < 0]["BFF_Area"].sum()

    net_balance = positive + negative

    df_short = pd.DataFrame({
        "Category": ["Blue-Green +", "Blue-Green -", "Netto Balance"],
        "Value": [positive, negative, net_balance]
    })

    total_color = "#5ECBC8" if net_balance >= 0 else "#CD4C46"

    fig = go.Figure(go.Waterfall(
        orientation="v",
        x=df_short["Category"],
        y=df_short["Value"],
        measure=["relative", "relative", "total"],
        connector={"line": {"color": "black", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": "#4A588A"}},
        decreasing={"marker": {"color": "#ECC846"}},
        totals={"marker": {"color": total_color}},
        text=[f"{v:.1f}" for v in df_short["Value"]],
        textposition="outside"
    ))

    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=2.5,
        y0=0,
        y1=0,
        line=dict(color="black", width=1, dash="dash")
    )

    fig.update_layout(
        title="Blue-Green-Infrastructure Balance (Summary) " + project_title,
        xaxis_title="Category",
        yaxis_title="Area",
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(size=13),
        margin=dict(l=60, r=40, t=80, b=80)
    )

    print("Plotting Short Waterfall Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, "waterfall_short.html"),
        auto_open=False
    )


import os
import pandas as pd
import plotly
import plotly.graph_objects as go


def sankey_plot(df, project_title, output_dir):
    df = df[df["BFF_Area"] != 0].copy()

    # ------------------------------------------------------------------
    # 1) Category scores (for testing: first value of your table)
    # ------------------------------------------------------------------
    category_score = {
        "Vegetationsfläche (hohes Grünvolumen)": 1.0,
        "Vegetationsfläche (mittleres Grünvolumen)": 0.75,
        "Vegetationsfläche (niedriges Grünvolumen)": 0.5,
        "Versiegelte Belagsfläche": 0.0,
        "Teilversiegelte Belagsfläche": 0.1,
        "Durchlässige Belagsfläche": 0.2,
        "Begrünte Belagsfläche": 0.4,
        "Gründach (extensiv)": 0.4,
        "Gründach (einfach-intensiv)": 0.7,
        "Vertikalbegrünung (bodengebunden)": 0.5,
        "Vertikalbegrünung (wandgebunden-horizontal)": 0.7,
        "Vertikalbegrünung (wandgebunden-vertikal)": 0.7,
    }

    # ------------------------------------------------------------------
    # 2) Node coloring by category type
    # ------------------------------------------------------------------
    green_categories = {
        "Vegetationsfläche (hohes Grünvolumen)",
        "Vegetationsfläche (mittleres Grünvolumen)",
        "Vegetationsfläche (niedriges Grünvolumen)",
        "Begrünte Belagsfläche",
        "Gründach (extensiv)",
        "Gründach (einfach-intensiv)",
        "Vertikalbegrünung (bodengebunden)",
        "Vertikalbegrünung (wandgebunden-horizontal)",
        "Vertikalbegrünung (wandgebunden-vertikal)",
    }

    grey_categories = {
        "Versiegelte Belagsfläche",
        "Teilversiegelte Belagsfläche",
        "Durchlässige Belagsfläche",
    }

    def node_color(label):
        if label in green_categories:
            return "#6FCF97"   # soft green
        elif label in grey_categories:
            return "#9AA0A6"   # grey
        return "#4A588A"       # fallback

    # ------------------------------------------------------------------
    # 3) Aggregate transitions
    # ------------------------------------------------------------------
    df_grouped = (
        df.groupby(["Before", "After"], as_index=False)["BFF_Area"]
        .sum()
    )

    # Sankey values must be positive magnitudes
    df_grouped["Flow_Area"] = df_grouped["BFF_Area"].abs()

    # ------------------------------------------------------------------
    # 4) Improvement logic for link colors
    # ------------------------------------------------------------------
    df_grouped["BeforeScore"] = df_grouped["Before"].map(category_score)
    df_grouped["AfterScore"] = df_grouped["After"].map(category_score)
    df_grouped["DeltaScore"] = df_grouped["AfterScore"] - df_grouped["BeforeScore"]

    def link_color(delta):
        if pd.isna(delta):
            return "rgba(120,120,120,0.35)"   # unknown
        elif delta > 0:
            return "rgba(74,88,138,0.45)"     # improvement -> blue
        elif delta < 0:
            return "rgba(205,76,70,0.45)"     # worsening -> red
        else:
            return "rgba(160,160,160,0.35)"   # neutral

    df_grouped["LinkColor"] = df_grouped["DeltaScore"].apply(link_color)

    # ------------------------------------------------------------------
    # 5) Build nodes
    # ------------------------------------------------------------------
    labels = list(pd.concat([df_grouped["Before"], df_grouped["After"]]).unique())
    label_to_index = {label: i for i, label in enumerate(labels)}
    node_colors = [node_color(label) for label in labels]

    # ------------------------------------------------------------------
    # 6) Hover text
    # ------------------------------------------------------------------
    hover_text = []
    for _, row in df_grouped.iterrows():
        hover_text.append(
            f"Transition: {row['Before']} → {row['After']}<br>"
            f"Area: {row['Flow_Area']:.1f}<br>"
            f"Before score: {row['BeforeScore']:.2f}<br>"
            f"After score: {row['AfterScore']:.2f}<br>"
            f"Delta: {row['DeltaScore']:.2f}"
        )

    # ------------------------------------------------------------------
    # 7) Figure
    # ------------------------------------------------------------------
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=22,
            line=dict(color="black", width=0.4),
            label=labels,
            color=node_colors
        ),
        link=dict(
            source=df_grouped["Before"].map(label_to_index),
            target=df_grouped["After"].map(label_to_index),
            value=df_grouped["Flow_Area"],
            color=df_grouped["LinkColor"],
            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Blue-Green-Infrastructure Transitions " + project_title,
        font=dict(size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=40, r=40, t=80, b=40)
    )

    print("Plotting Sankey Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, "sankey_plot.html"),
        auto_open=False
    )
