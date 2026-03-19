import os
import pandas as pd
import plotly
import plotly.graph_objects as go


# ============================================================
# SOLID / CLEAN DESIGN
# ============================================================
COLORS = {
    "bg": "#FFFFFF",
    "paper": "#FFFFFF",
    "grid": "#E5E7EB",
    "text": "#1F2937",
    "muted": "#6B7280",
    "line": "#9CA3AF",

    "pos": "#6FAFC7",          # heller / lebendiger
    "neg": "#A7B1BF",          # ruhig neutral
    "total_pos": "#3E6676",    # dunkleres Petrol
    "total_neg": "#7C4F4F",    # nur falls net total negativ ist
    "highlight": "rgba(62,102,118,0.05)",

    "node_green": "#79B7CC",
    "node_grey": "#B6BFCA",
    "node_blue": "#5E7D8A",

    "link_pos": "rgba(111,175,199,0.38)",
    "link_neg": "rgba(167,177,191,0.28)",
    "link_neutral": "rgba(182,191,202,0.20)",
    "link_unknown": "rgba(94,125,138,0.16)",
}


# ============================================================
# LABELS / FACTORS
# ============================================================
SHORT_LABELS = {
    "Vegetationsfläche (hohes Grünvolumen)": "Vegetation hoch",
    "Vegetationsfläche (mittleres Grünvolumen)": "Vegetation mittel",
    "Vegetationsfläche (niedriges Grünvolumen)": "Vegetation niedrig",
    "Versiegelte Belagsfläche": "Versiegelt",
    "Teilversiegelte Belagsfläche": "Teilversiegelt",
    "Durchlässige Belagsfläche": "Durchlässig",
    "Begrünte Belagsfläche": "Begrünter Belag",
    "Gründach (extensiv)": "Gründach ext.",
    "Gründach (einfach-intensiv)": "Gründach int.",
    "Vertikalbegrünung (bodengebunden)": "Vertikalgrün Boden",
    "Vertikalbegrünung (wandgebunden-horizontal)": "Vertikalgrün horiz.",
    "Vertikalbegrünung (wandgebunden-vertikal)": "Vertikalgrün vert.",
}

# Später am besten aus externer Tabelle / Config ziehen
FACTOR_LABELS = {
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


def short_label(label):
    return SHORT_LABELS.get(label, str(label))


def factor_value(label):
    return FACTOR_LABELS.get(label, None)


def factor_label(label):
    val = factor_value(label)
    if val is None:
        return "?"
    return f"{val:g}"


def unique_labels(labels):
    counts = {}
    result = []
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
        if counts[label] == 1:
            result.append(label)
        else:
            result.append(f"{label} ·{counts[label]}")
    return result


def build_transition_label(before, after):
    # kompakt, aber eindeutig genug
    return f"{short_label(before)} → {short_label(after)}"


def apply_layout(fig, title, xaxis_title="", yaxis_title="", height=760):
    fig.update_layout(
        title=dict(
            text=title,
            x=0.01,
            xanchor="left",
            font=dict(size=22, color=COLORS["text"])
        ),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(
            family="Inter, Arial, Helvetica, sans-serif",
            size=13,
            color=COLORS["text"]
        ),
        margin=dict(l=70, r=30, t=85, b=120),
        height=height,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D1D5DB",
            font=dict(
                family="Inter, Arial, sans-serif",
                size=12,
                color="#111827"
            ),
            align="left"
        ),
        xaxis=dict(
            title=xaxis_title,
            showgrid=False,
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=COLORS["muted"]),
            title_font=dict(size=12, color=COLORS["muted"]),
            automargin=True
        ),
        yaxis=dict(
            title=yaxis_title,
            showgrid=True,
            gridcolor=COLORS["grid"],
            gridwidth=0.8,
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=COLORS["muted"]),
            title_font=dict(size=12, color=COLORS["muted"])
        )
    )


# ============================================================
# WATERFALL
# ============================================================
def waterfall(df, project_title, output_dir, min_share_of_max=0.01):
    """
    Waterfall plot with optional filtering of very small contributions.

    Parameters
    ----------
    min_share_of_max : float or None
        Relative threshold based on the largest absolute BFF_Area value.
        Example: 0.02 means all transitions with abs(BFF_Area) < 0.2% of the
        maximum absolute contribution are hidden.
        Final Balance still uses the full unfiltered dataset.
    """
    df = df[df["BFF_Area"] != 0].copy()

    if df.empty:
        print("No non-zero values for waterfall plot.")
        return

    # sort once for reference
    df = df.reindex(df["BFF_Area"].abs().sort_values(ascending=False).index).reset_index(drop=True)

    # --------------------------------------------------------
    # Final balance always from FULL dataset
    # --------------------------------------------------------
    net_balance = df["BFF_Area"].sum()

    # --------------------------------------------------------
    # Optional filtering of small displayed values
    # --------------------------------------------------------
    filtered_count = 0
    threshold_value = None
    original_count = len(df)

    df_display = df.copy()

    if min_share_of_max is not None and min_share_of_max > 0:
        max_abs = df_display["BFF_Area"].abs().max()

        if pd.notna(max_abs) and max_abs > 0:
            threshold_value = max_abs * float(min_share_of_max)

            mask_keep = df_display["BFF_Area"].abs() >= threshold_value
            filtered_count = int((~mask_keep).sum())
            df_display = df_display.loc[mask_keep].copy().reset_index(drop=True)

    if df_display.empty:
        print("All display values were filtered out in waterfall plot.")
        return

    # compact x labels
    df_display["XBase"] = df_display.apply(
        lambda r: build_transition_label(r["Before"], r["After"]),
        axis=1
    )
    df_display["XLabel"] = unique_labels(df_display["XBase"].tolist())

    # full hover
    df_display["HoverLabel"] = df_display.apply(
        lambda r: (
            f"<b>{r['Before']} → {r['After']}</b><br>"
            f"Before factor: {factor_label(r['Before'])}<br>"
            f"After factor: {factor_label(r['After'])}<br>"
            f"Balance contribution: {r['BFF_Area']:.1f}"
        ),
        axis=1
    )

    df_total = pd.DataFrame({
        "XLabel": ["Net Balance"],
        "BFF_Area": [net_balance],
        "HoverLabel": [(
            f"<b>Net Balance</b><br>"
            f"Area: {net_balance:.1f}<br>"
            f"Includes all transitions"
        )]
    })

    df_plot = pd.concat(
        [df_display[["XLabel", "BFF_Area", "HoverLabel"]], df_total],
        ignore_index=True
    )

    total_idx = len(df_plot) - 1
    total_color = COLORS["total_pos"] if net_balance >= 0 else COLORS["total_neg"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        x=df_plot["XLabel"],
        y=df_plot["BFF_Area"],
        measure=["relative"] * (len(df_plot) - 1) + ["total"],
        connector={
            "line": {"color": COLORS["line"], "width": 0.8, "dash": "dot"}
        },
        increasing={"marker": {"color": COLORS["pos"]}},
        decreasing={"marker": {"color": COLORS["neg"]}},
        totals={"marker": {"color": total_color}},
        text=[f"{v:.1f}" for v in df_plot["BFF_Area"]],
        textposition="outside",
        textfont=dict(size=11, color=COLORS["text"]),
        customdata=df_plot["HoverLabel"],
        hovertemplate="%{customdata}<extra></extra>"
    ))

    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=len(df_plot) - 0.5,
        y0=0,
        y1=0,
        line=dict(color=COLORS["line"], width=1.0, dash="dash")
    )

    fig.add_vrect(
        x0=total_idx - 0.5,
        x1=total_idx + 0.5,
        fillcolor=COLORS["highlight"],
        opacity=1,
        line_width=0
    )

    fig.add_annotation(
        x=total_idx,
        y=net_balance,
        text="Final balance",
        showarrow=False,
        yshift=22 if net_balance >= 0 else -22,
        font=dict(size=11, color=COLORS["muted"])
    )

    apply_layout(
        fig,
        title=f"Blue–Green Infrastructure Balance — {project_title}",
        xaxis_title="Transformation",
        yaxis_title="Area",
        height=max(760, 520 + len(df_plot) * 10)
    )

    fig.update_xaxes(tickangle=-18)

    # --------------------------------------------------------
    # Info box about filtering
    # Place it inside the plotting area, top-right
    # --------------------------------------------------------
    if filtered_count > 0 and threshold_value is not None:
        shown_count = original_count - filtered_count

        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.99,
            y=0.02,
            xanchor="right",
            yanchor="bottom",
            align="left",
            showarrow=False,
            text=(
                f"{filtered_count} Note: small transitions hidden,"
                f"<br><span style='font-size:11px'>"
                f"Shown: {shown_count} of {original_count}"
                f"<br>Threshold: {min_share_of_max:.1%} of max = {threshold_value:.0f}"
                f"<br>Net balance includes all values."
                f"</span>"
            ),
            font=dict(size=11, color=COLORS["muted"]),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=COLORS["grid"],
            borderwidth=1,
            borderpad=6
        )

    print("Plotting Waterfall Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, "plot_waterfall_" + project_title + ".html"),
        auto_open=False
    )


# ============================================================
# WATERFALL SHORT
# ============================================================
def waterfall_short(df, project_title, output_dir):
    df = df[df["BFF_Area"] != 0].copy()

    positive = df.loc[df["BFF_Area"] > 0, "BFF_Area"].sum()
    negative = df.loc[df["BFF_Area"] < 0, "BFF_Area"].sum()
    net_balance = positive + negative

    df_short = pd.DataFrame({
        "Category": ["Gain", "Loss", "Net Balance"],
        "Value": [positive, negative, net_balance],
        "Hover": [
            f"<b>Positive balance contributions</b><br>Area: {positive:.1f}",
            f"<b>Negative balance contributions</b><br>Area: {negative:.1f}",
            f"<b>Net Balance</b><br>Area: {net_balance:.1f}",
        ]
    })

    total_color = COLORS["total_pos"] if net_balance >= 0 else COLORS["total_neg"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        x=df_short["Category"],
        y=df_short["Value"],
        measure=["relative", "relative", "total"],
        connector={
            "line": {"color": COLORS["line"], "width": 0.8, "dash": "dot"}
        },
        increasing={"marker": {"color": COLORS["pos"]}},
        decreasing={"marker": {"color": COLORS["neg"]}},
        totals={"marker": {"color": total_color}},
        text=[f"{v:.1f}" for v in df_short["Value"]],
        textposition="outside",
        textfont=dict(size=12, color=COLORS["text"]),
        customdata=df_short["Hover"],
        hovertemplate="%{customdata}<extra></extra>"
    ))

    fig.add_shape(
        type="line",
        x0=-0.5,
        x1=2.5,
        y0=0,
        y1=0,
        line=dict(color=COLORS["line"], width=1.0, dash="dash")
    )

    fig.add_vrect(
        x0=1.5,
        x1=2.5,
        fillcolor=COLORS["highlight"],
        opacity=1,
        line_width=0
    )

    apply_layout(
        fig,
        title=f"Blue–Green Infrastructure Balance — Summary — {project_title}",
        xaxis_title="Category",
        yaxis_title="Area",
        height=620
    )

    fig.update_xaxes(tickangle=0)

    print("Plotting Short Waterfall Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, "plot_waterfall_short_" + project_title + ".html"),
        auto_open=False
    )


# ============================================================
# SANKEY
# ============================================================
def sankey_plot(df, project_title, output_dir):
    df = df[df["BFF_Area"] != 0].copy()

    # group transitions
    df_grouped = (
        df.groupby(["Before", "After"], as_index=False)["BFF_Area"]
        .sum()
    )

    # Sankey values as positive magnitudes
    df_grouped["Flow_Area"] = df_grouped["BFF_Area"].abs()

    # factors
    df_grouped["BeforeScore"] = df_grouped["Before"].map(FACTOR_LABELS)
    df_grouped["AfterScore"] = df_grouped["After"].map(FACTOR_LABELS)
    df_grouped["DeltaScore"] = df_grouped["AfterScore"] - df_grouped["BeforeScore"]

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
            return COLORS["node_green"]
        elif label in grey_categories:
            return COLORS["node_grey"]
        return COLORS["node_blue"]

    def link_color(delta):
        if pd.isna(delta):
            return COLORS["link_unknown"]
        elif delta > 0:
            return COLORS["link_pos"]
        elif delta < 0:
            return COLORS["link_neg"]
        else:
            return COLORS["link_neutral"]

    df_grouped["LinkColor"] = df_grouped["DeltaScore"].apply(link_color)

    labels = list(pd.concat([df_grouped["Before"], df_grouped["After"]]).unique())
    label_to_index = {label: i for i, label in enumerate(labels)}
    node_colors = [node_color(label) for label in labels]
    short_labels = [short_label(l) for l in labels]

    hover_text = []
    for _, row in df_grouped.iterrows():
        before_score = "?" if pd.isna(row["BeforeScore"]) else f"{row['BeforeScore']:.2f}"
        after_score = "?" if pd.isna(row["AfterScore"]) else f"{row['AfterScore']:.2f}"
        delta_score = "?" if pd.isna(row["DeltaScore"]) else f"{row['DeltaScore']:.2f}"

        hover_text.append(
            f"<b>{row['Before']} → {row['After']}</b><br>"
            f"Area: {row['Flow_Area']:.1f}<br>"
            f"Before factor: {before_score}<br>"
            f"After factor: {after_score}<br>"
            f"Delta: {delta_score}"
        )

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=22,
            thickness=18,
            line=dict(color="rgba(100,116,139,0.18)", width=0.6),
            label=short_labels,
            color=node_colors,
            customdata=labels,
            hovertemplate="<b>%{customdata}</b><extra></extra>"
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
        title=dict(
            text=f"Blue–Green Infrastructure Transitions — {project_title}",
            x=0.01,
            xanchor="left",
            font=dict(size=22, color=COLORS["text"])
        ),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["bg"],
        font=dict(
            family="Inter, Arial, Helvetica, sans-serif",
            size=13,
            color=COLORS["text"]
        ),
        margin=dict(l=30, r=30, t=85, b=30),
        height=760,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D1D5DB",
            font=dict(
                family="Inter, Arial, sans-serif",
                size=12,
                color="#111827"
            ),
            align="left"
        )
    )

    print("Plotting Sankey Diagram.")
    plotly.offline.plot(
        fig,
        filename=os.path.join(output_dir, project_title + "plot_sankey_" + project_title + ".html"),
        auto_open=False
    )
