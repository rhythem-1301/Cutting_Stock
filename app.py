import streamlit as st
import pulp
import pandas as pd

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Cutting Optimizer",
    layout="wide"
)

st.title("Cutting Optimization Dashboard")
st.caption("Optimize large roll selection with minimum waste and material usage")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header(" Input Parameters")

    reel_input = st.text_input(
        "Large Roll Widths (inches)",
        "18, 20, 22"
    )
    slit_input = st.text_input(
        "Demand Widths (inches)",
        "9, 8, 7"
    )

    large_rolls = [int(x.strip()) for x in reel_input.split(",") if x.strip()]
    customer_sizes = [int(x.strip()) for x in slit_input.split(",") if x.strip()]

    order_demand = {}
    if customer_sizes:
        st.subheader(" Order Quantities")
        for size in customer_sizes:
            order_demand[size] = st.number_input(
                f"{size} inches",
                min_value=1,
                value=10
            )

# ---------------- LOGIC ----------------
def generate_cutting_patterns(roll_width, sizes, min_size):
    patterns = []

    def backtrack(i, used, counts):
        if i == len(sizes):
            scrap = roll_width - used
            if 0 <= scrap < min_size:
                patterns.append(tuple(counts))
            return
        max_cuts = (roll_width - used) // sizes[i]
        for c in range(max_cuts + 1):
            backtrack(i + 1, used + c * sizes[i], counts + [c])

    backtrack(0, 0, [])
    return patterns

# ---------------- RUN ----------------
if st.button(" Run Optimization"):

    if not large_rolls or not customer_sizes:
        st.error("Please enter valid roll widths and demand sizes.")
        st.stop()

    min_size = min(customer_sizes)
    simulation_results = []

    st.divider()
    st.header("Optimization Results")

    for roll_width in large_rolls:
        patterns = generate_cutting_patterns(
            roll_width, customer_sizes, min_size
        )

        model = pulp.LpProblem(
            f"Optimize_{roll_width}",
            pulp.LpMinimize
        )

        x = pulp.LpVariable.dicts(
            "Pattern",
            range(len(patterns)),
            lowBound=0,
            cat="Integer"
        )

        model += pulp.lpSum(x[j] for j in range(len(patterns)))

        for i, size in enumerate(customer_sizes):
            model += pulp.lpSum(
                patterns[j][i] * x[j]
                for j in range(len(patterns))
            ) >= order_demand[size]

        model.solve(pulp.PULP_CBC_CMD(msg=0))

        total_rolls = sum(pulp.value(x[j]) for j in range(len(patterns)))
        total_material = int(total_rolls * roll_width)

        pattern_rows = []
        total_scrap = 0

        for j, p in enumerate(patterns):
            count = int(pulp.value(x[j]))
            if count > 0:
                used_width = sum(
                    p[i] * customer_sizes[i]
                    for i in range(len(customer_sizes))
                )
                scrap = roll_width - used_width
                total_scrap += scrap * count

                pattern_rows.append({
                    "Pattern": dict(zip(customer_sizes, p)),
                    "Rolls Used": count,
                    "Scrap / Roll (mm)": scrap,
                    "Total Scrap (mm)": scrap * count
                })

        df = pd.DataFrame(pattern_rows)

        with st.expander(f" Roll Width: {roll_width} inches", expanded=False):
            col1, col2, col3 = st.columns(3)

            col1.metric("Total Rolls Used", int(total_rolls))
            col2.metric("Total Material Used (inches)", total_material)
            col3.metric("Total Scrap (inches)", total_scrap)

            st.subheader(" Cutting Patterns Used")
            st.dataframe(df, use_container_width=True)

        simulation_results.append({
            "RollWidth": roll_width,
            "TotalMaterial": total_material,
            "TotalScrap": total_scrap
        })

    # ---------------- FINAL DECISION ----------------
    best = min(simulation_results, key=lambda x: x["TotalMaterial"])

    st.divider()
    st.header(" Final Recommendation")

    st.success(
        f"""
        **Optimal Roll Width Selected: {best['RollWidth']} inches**

        **Why this option?**
        - Uses the **least total material**
        - Minimizes overall production waste
        - Meets all customer demand efficiently

        **Key Outcome**
        - Total Material Used: **{best['TotalMaterial']} inches**
        - Total Scrap Generated: **{best['TotalScrap']} inches**
        """
    )

    st.caption(
        "📌 Decision is based on minimizing total material consumption while fulfilling all order requirements."
    )
