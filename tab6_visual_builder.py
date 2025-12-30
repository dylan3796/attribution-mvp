# ============================================================================
# TAB 6: VISUAL RULE BUILDER (SIMPLIFIED UX)
# ============================================================================

with tabs[6]:
    st.title("🎨 Build Your Attribution Rule")
    st.caption("No coding required - just drag sliders and see results instantly")

    # Quick start templates
    st.markdown("### 🚀 Quick Start")
    st.markdown("Pick a template or build from scratch:")

    template_cols = st.columns(4)

    template_selected = None
    with template_cols[0]:
        if st.button("⚡ Equal Split\n*All partners get equal credit*", width='stretch', key="tmpl_equal"):
            template_selected = "equal"

    with template_cols[1]:
        if st.button("🎯 60/30/10 Split\n*SI 60%, Influence 30%, Referral 10%*", width='stretch', key="tmpl_603010"):
            template_selected = "603010"

    with template_cols[2]:
        if st.button("🏆 Winner Takes All\n*First partner gets 100%*", width='stretch', key="tmpl_winner"):
            template_selected = "winner"

    with template_cols[3]:
        if st.button("🔨 Custom\n*Build your own rule*", width='stretch', key="tmpl_custom"):
            template_selected = "custom"

    st.markdown("---")

    # Initialize session state for rule builder
    if "visual_builder" not in st.session_state:
        st.session_state.visual_builder = {
            "rule_name": "My Custom Rule",
            "roles": ["Implementation (SI)", "Referral"],
            "splits": {"Implementation (SI)": 70, "Referral": 30},
            "applies_to_all": True,
            "min_deal_size": 0
        }

    # Apply template if selected
    if template_selected == "equal":
        st.session_state.visual_builder["rule_name"] = "Equal Split"
        st.session_state.visual_builder["splits"] = {
            role: 100 // len(DEFAULT_PARTNER_ROLES)
            for role in DEFAULT_PARTNER_ROLES[:3]
        }
        st.session_state.visual_builder["roles"] = DEFAULT_PARTNER_ROLES[:3]

    elif template_selected == "603010":
        st.session_state.visual_builder["rule_name"] = "60/30/10 Split"
        st.session_state.visual_builder["splits"] = {
            "Implementation (SI)": 60,
            "Influence": 30,
            "Referral": 10
        }
        st.session_state.visual_builder["roles"] = ["Implementation (SI)", "Influence", "Referral"]

    elif template_selected == "winner":
        st.session_state.visual_builder["rule_name"] = "Winner Takes All"
        st.session_state.visual_builder["splits"] = {"First Touch": 100}
        st.session_state.visual_builder["roles"] = ["First Touch"]

    # Step 1: Which deals does this apply to?
    st.markdown("### 1️⃣ Which deals should use this rule?")

    col1, col2 = st.columns(2)

    with col1:
        applies_to = st.radio(
            "",
            ["All deals", "Deals over a certain size", "Specific products"],
            key="applies_to_radio",
            horizontal=False
        )

        st.session_state.visual_builder["applies_to_all"] = (applies_to == "All deals")

    with col2:
        if applies_to == "Deals over a certain size":
            min_size = st.slider(
                "Minimum deal value",
                min_value=0,
                max_value=500000,
                value=100000,
                step=10000,
                format="$%d",
                key="min_deal_slider"
            )
            st.session_state.visual_builder["min_deal_size"] = min_size
            st.info(f"This rule applies to deals worth **${min_size:,}** or more")
        elif applies_to == "Specific products":
            product_filter = st.text_input(
                "Product/Service",
                placeholder="e.g., Enterprise Plan, Professional Services",
                key="product_filter"
            )

    st.markdown("---")

    # Step 2: Build the split
    st.markdown("### 2️⃣ How should we split credit among partners?")

    # Role selection
    st.markdown("**Select partner roles:**")
    selected_roles = st.multiselect(
        "",
        options=DEFAULT_PARTNER_ROLES,
        default=st.session_state.visual_builder.get("roles", ["Implementation (SI)", "Referral"]),
        key="role_multiselect",
        help="Choose which partner roles should get credit"
    )

    if len(selected_roles) == 0:
        st.warning("⚠️ Please select at least one partner role")
        st.stop()

    st.session_state.visual_builder["roles"] = selected_roles

    st.markdown("**Adjust credit split:**")

    # Visual sliders for each role
    splits = {}
    total_allocated = 0

    for role in selected_roles:
        # Get previous value or default
        default_value = st.session_state.visual_builder["splits"].get(role, 100 // len(selected_roles))

        col1, col2 = st.columns([3, 1])

        with col1:
            split_pct = st.slider(
                f"{role}",
                min_value=0,
                max_value=100,
                value=int(default_value),
                step=5,
                key=f"split_{role}",
                help=f"Percentage of deal value attributed to {role}"
            )

        with col2:
            st.metric("Percentage", f"{split_pct}%", label_visibility="collapsed")

        splits[role] = split_pct
        total_allocated += split_pct

    st.session_state.visual_builder["splits"] = splits

    # Validation
    st.markdown("---")

    if total_allocated != 100:
        st.error(f"❌ **Total is {total_allocated}%** (must equal 100%)")
        st.markdown("Adjust the sliders above so they add up to 100%")
    else:
        st.success(f"✅ **Perfect!** Splits add up to 100%")

    # Step 3: Live Preview
    st.markdown("---")
    st.markdown("### 3️⃣ Preview")

    # Example deal preview
    st.markdown("**Example: $100,000 Deal**")

    preview_data = []
    for role, pct in splits.items():
        amount = 100000 * (pct / 100)
        preview_data.append({
            "Partner Role": role,
            "Split": f"{pct}%",
            "Amount": f"${amount:,.0f}"
        })

    # Show as a nice table
    import pandas as pd
    preview_df = pd.DataFrame(preview_data)
    st.dataframe(preview_df, width='stretch', hide_index=True)

    # Visual bar chart
    import plotly.graph_objects as go

    fig = go.Figure(data=[
        go.Bar(
            x=list(splits.values()),
            y=list(splits.keys()),
            orientation='h',
            text=[f"{v}%" for v in splits.values()],
            textposition='inside',
            marker=dict(
                color=['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'][:len(splits)]
            )
        )
    ])

    fig.update_layout(
        title="Credit Split Visualization",
        xaxis_title="Percentage (%)",
        yaxis_title="Partner Role",
        height=300,
        showlegend=False
    )

    st.plotly_chart(fig, width='stretch')

    # Step 4: Save
    st.markdown("---")
    st.markdown("### 4️⃣ Save Your Rule")

    col1, col2 = st.columns([2, 1])

    with col1:
        rule_name = st.text_input(
            "Rule Name",
            value=st.session_state.visual_builder.get("rule_name", "My Custom Rule"),
            placeholder="e.g., '60/30/10 Enterprise Split'",
            key="rule_name_input"
        )

    with col2:
        st.markdown("")  # Spacing
        st.markdown("")

        if total_allocated == 100 and rule_name:
            if st.button("💾 Save Rule", type="primary", width='stretch', key="save_visual_rule"):
                # Create the rule
                new_rule = AttributionRule(
                    id=len(st.session_state.rules) + 1,
                    name=rule_name,
                    model_type=AttributionModel.ROLE_WEIGHTED,
                    config={"weights": {role: pct/100 for role, pct in splits.items()}},
                    split_constraint=SplitConstraint.MUST_SUM_TO_100,
                    applies_to={
                        "min_value": st.session_state.visual_builder.get("min_deal_size", 0)
                    } if not st.session_state.visual_builder.get("applies_to_all", True) else {},
                    priority=100,
                    active=True
                )

                st.session_state.rules.append(new_rule)

                # Recalculate attribution
                with st.spinner("💡 Applying your new rule..."):
                    count = calculate_attribution_for_all_targets()

                st.success(f"✅ Rule '{rule_name}' saved! Created {count} ledger entries")
                st.balloons()

                # Reset builder
                st.session_state.visual_builder = {
                    "rule_name": "My Custom Rule",
                    "roles": ["Implementation (SI)", "Referral"],
                    "splits": {"Implementation (SI)": 70, "Referral": 30},
                    "applies_to_all": True,
                    "min_deal_size": 0
                }

                st.rerun()
        else:
            st.button("💾 Save Rule", type="primary", width='stretch', disabled=True, key="save_visual_rule_disabled")
            if total_allocated != 100:
                st.caption("⚠️ Fix the split percentages first")
            elif not rule_name:
                st.caption("⚠️ Enter a rule name first")

    # Advanced: Natural Language Option
    with st.expander("💬 Or describe your rule in plain English (Advanced)", expanded=False):
        st.markdown("**Describe your attribution model:**")
        nl_input = st.text_area(
            "",
            placeholder="e.g., 'Give 70% to SI partners and 30% to referral partners for enterprise deals'",
            height=100,
            key="nl_advanced"
        )

        if st.button("🚀 Generate from Description", key="nl_generate"):
            if nl_input:
                st.info("💡 Natural language parsing coming soon! For now, use the visual builder above.")
            else:
                st.warning("Please enter a description first")
