import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Delivery Planner System", page_icon="🚚", layout="wide"
)

# ---------------------------------------------------------
# 1. LOAD & PREPARE MASTER DATA FROM EXCEL
# ---------------------------------------------------------
MASTER_FILE = "ALL MASTER.xlsx"


@st.cache_data
def load_master_data():
    df_raw = pd.read_excel(MASTER_FILE, sheet_name="Sheet1")

    # Master Kendaraan (13 Data Pertama)
    df_fleet = (
        df_raw[
            ["NOPOL", "SOPIR", "JENIS KENDARAAN", "KERNET", "KAPASITAS (TON)"]
        ]
        .dropna(subset=["NOPOL"])
        .reset_index(drop=True)
    )

    # Master Barang
    df_items = (
        df_raw[["NAMA BARANG", "SKU", "BERAT (TON)"]]
        .dropna(subset=["SKU"])
        .reset_index(drop=True)
    )

    # Master Customer
    df_customers = (
        df_raw[["TUJUAN / PELANGGAN", "ALAMAT KIRIM"]]
        .dropna(subset=["TUJUAN / PELANGGAN"])
        .reset_index(drop=True)
    )

    return df_fleet, df_items, df_customers


df_fleet, df_items, df_customers = load_master_data()

# Initialize Session State untuk menyimpan Order dan Planning Data
if "orders" not in st.session_state:
    st.session_state.orders = pd.DataFrame(
        columns=[
            "Order_ID",
            "Customer",
            "Alamat",
            "SKU",
            "Nama_Barang",
            "Qty",
            "Total_Tonase",
            "Status",
            "Assigned_Nopol",
        ]
    )

if "order_counter" not in st.session_state:
    st.session_state.order_counter = 1

# ---------------------------------------------------------
# NAVIGATION & SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("🚚 Navigasi Sistem")
menu = st.sidebar.radio(
    "Pilih Menu:",
    [
        "📊 Dashboard",
        "🛒 Input Order Baru",
        "🚛 Manual Planner Kiriman",
        "🤖 Auto Planner (Rekomendasi)",
        "📋 Monitoring & Surat Jalan",
    ],
)

# ---------------------------------------------------------
# MENU 1: DASHBOARD
# ---------------------------------------------------------
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Operasional Kiriman")

    orders_df = st.session_state.orders

    total_orders = len(orders_df)
    total_tonase = (
        orders_df["Total_Tonase"].sum() if not orders_df.empty else 0.0
    )

    planned_orders = len(orders_df[orders_df["Status"] == "Planned"])
    unplanned_orders = len(orders_df[orders_df["Status"] == "Unplanned"])

    used_nopol = (
        orders_df[orders_df["Status"] == "Planned"]["Assigned_Nopol"]
        .nunique()
        if not orders_df.empty
        else 0
    )
    total_fleet = len(df_fleet)
    available_fleet = total_fleet - used_nopol

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Order Hari Ini", f"{total_orders} Order")
    col2.metric("Total Tonase Muatan", f"{total_tonase:.2f} Ton")
    col3.metric(
        "Armada Terpakai",
        f"{used_nopol} / {total_fleet}",
        f"{available_fleet} Tersedia",
    )
    col4.metric(
        "Status Order",
        f"{planned_orders} Planned",
        f"{unplanned_orders} Unplanned",
        delta_color="inverse",
    )

    st.divider()
    st.subheader("📦 Ringkasan Status Order")
    if not orders_df.empty:
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("Belum ada order yang diinputkan hari ini.")

# ---------------------------------------------------------
# MENU 2: INPUT ORDER BARU
# ---------------------------------------------------------
elif menu == "🛒 Input Order Baru":
    st.title("🛒 Input Order Sales / Kiriman Baru")

    with st.form("input_order_form"):
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            customer = st.selectbox(
                "Pilih Pelanggan / Tujuan:",
                options=df_customers["TUJUAN / PELANGGAN"].unique(),
            )
            # Auto fetch alamat berdasarkan customer
            alamat_list = df_customers[
                df_customers["TUJUAN / PELANGGAN"] == customer
            ]["ALAMAT KIRIM"].tolist()
            alamat = st.selectbox("Alamat Kirim:", options=alamat_list)

        with col_c2:
            item_selected = st.selectbox(
                "Pilih Barang / SKU:",
                options=df_items["NAMA BARANG"] + " (" + df_items["SKU"] + ")",
            )
            sku = item_selected.split("(")[-1].replace(")", "").strip()
            nama_barang = df_items[df_items["SKU"] == sku][
                "NAMA BARANG"
            ].values[0]
            berat_per_unit = df_items[df_items["SKU"] == sku][
                "BERAT (TON)"
            ].values[0]

            qty = st.number_input(
                "Jumlah (Qty / Koli / Pcs):", min_value=1, value=100
            )
            calculated_tonase = qty * berat_per_unit
            st.info(
                f"Estimasi Tonase: **{calculated_tonase:.3f} Ton** (Berat Satuan: {berat_per_unit} Ton)"
            )

        submit = st.form_submit_button("➕ Tambahkan Order ke Antrean")

        if submit:
            new_order = {
                "Order_ID": f"ORD-{st.session_state.order_counter:03d}",
                "Customer": customer,
                "Alamat": alamat,
                "SKU": sku,
                "Nama_Barang": nama_barang,
                "Qty": qty,
                "Total_Tonase": round(calculated_tonase, 3),
                "Status": "Unplanned",
                "Assigned_Nopol": "-",
            }
            st.session_state.orders = pd.concat(
                [st.session_state.orders, pd.DataFrame([new_order])],
                ignore_index=True,
            )
            st.session_state.order_counter += 1
            st.success(f"Order {new_order['Order_ID']} berhasil ditambahkan!")

    st.subheader("📋 Daftar Antrean Order (Belum Ter-planner)")
    unplanned = st.session_state.orders[
        st.session_state.orders["Status"] == "Unplanned"
    ]
    st.dataframe(unplanned, use_container_width=True)

# ---------------------------------------------------------
# MENU 3: MANUAL PLANNER KIRIMAN
# ---------------------------------------------------------
elif menu == "🚛 Manual Planner Kiriman":
    st.title("🚛 Penjadwalan & Plotting Armada (Manual)")

    unplanned_orders = st.session_state.orders[
        st.session_state.orders["Status"] == "Unplanned"
    ]

    if unplanned_orders.empty:
        st.success("Semua order telah di-planner!")
    else:
        st.subheader("1. Pilih Order yang Akan Diangkut")
        selected_order_ids = st.multiselect(
            "Pilih Order ID:",
            options=unplanned_orders["Order_ID"].tolist(),
            format_func=lambda x: f"{x} - {unplanned_orders[unplanned_orders['Order_ID']==x]['Customer'].values[0]} ({unplanned_orders[unplanned_orders['Order_ID']==x]['Total_Tonase'].values[0]} Ton)",
        )

        if selected_order_ids:
            selected_df = unplanned_orders[
                unplanned_orders["Order_ID"].isin(selected_order_ids)
            ]
            total_selected_tonase = selected_df["Total_Tonase"].sum()

            st.write(
                f"**Total Tonase Dipilih:** `{total_selected_tonase:.3f} Ton`"
            )

            st.subheader("2. Alokasikan ke Kendaraan")
            nopol_choice = st.selectbox(
                "Pilih Armada:",
                options=df_fleet["NOPOL"]
                + " - "
                + df_fleet["JENIS KENDARAAN"]
                + " ("
                + df_fleet["SOPIR"]
                + ")",
            )

            selected_nopol = nopol_choice.split(" - ")[0]
            fleet_info = df_fleet[df_fleet["NOPOL"] == selected_nopol].iloc[0]
            kapasitas = fleet_info["KAPASITAS (TON)"]

            # INDIKATOR CAPACITY CHECKER
            st.write("---")
            st.write("### ⚖️ Indikator Muatan vs Kapasitas")

            col_a, col_b = st.columns(2)
            col_a.write(f"**Kendaraan:** {fleet_info['NOPOL']} ({fleet_info['JENIS KENDARAAN']})")
            col_a.write(f"**Sopir / Kernet:** {fleet_info['SOPIR']} / {fleet_info['KERNET']}")
            col_b.write(f"**Muatan Planned:** {total_selected_tonase:.3f} Ton")
            col_b.write(f"**Kapasitas Maksimal:** {kapasitas:.1f} Ton")

            percentage = min((total_selected_tonase / kapasitas), 1.0)
            st.progress(percentage)

            if total_selected_tonase <= kapasitas:
                st.success(
                    f"✅ **AMAN**: Muatan {total_selected_tonase:.2f} Ton / Kapasitas {kapasitas} Ton"
                )
                if st.button("💾 Simpan Alokasi Kiriman"):
                    # Update status di session state
                    st.session_state.orders.loc[
                        st.session_state.orders["Order_ID"].isin(
                            selected_order_ids
                        ),
                        "Status",
                    ] = "Planned"
                    st.session_state.orders.loc[
                        st.session_state.orders["Order_ID"].isin(
                            selected_order_ids
                        ),
                        "Assigned_Nopol",
                    ] = selected_nopol
                    st.success("Plotting kiriman berhasil disimpan!")
                    st.rerun()
            else:
                st.error(
                    f"🚨 **OVER CAPACITY**: Muatan {total_selected_tonase:.2f} Ton melebihi Kapasitas Armada ({kapasitas} Ton)!"
                )

# ---------------------------------------------------------
# MENU 4: AUTO PLANNER (ALGORITMA REKOMENDASI)
# ---------------------------------------------------------
elif menu == "🤖 Auto Planner (Rekomendasi)":
    st.title("🤖 Auto Planner & Grouping Kiriman")
    st.write(
        "Fitur ini mengelompokkan order yang belum ter-planner secara otomatis berdasarkan efisiensi kapasitas armada."
    )

    unplanned_df = st.session_state.orders[
        st.session_state.orders["Status"] == "Unplanned"
    ].copy()

    if unplanned_df.empty:
        st.info("Tidak ada order terbuka yang perlu di-planner.")
    else:
        if st.button("⚡ Jalankan Auto-Planner"):
            # Algoritma sederhana Bin Packing / Greedy Allocation
            available_fleets = df_fleet.copy()
            assignments = []

            for idx, fleet in available_fleets.iterrows():
                nopol = fleet["NOPOL"]
                cap = fleet["KAPASITAS (TON)"]
                current_load = 0.0
                assigned_orders = []

                for o_idx, order in unplanned_df[
                    unplanned_df["Status"] == "Unplanned"
                ].iterrows():
                    if current_load + order["Total_Tonase"] <= cap:
                        current_load += order["Total_Tonase"]
                        assigned_orders.append(order["Order_ID"])
                        unplanned_df.loc[
                            unplanned_df["Order_ID"] == order["Order_ID"],
                            "Status",
                        ] = "Assigned_Temp"

                if assigned_orders:
                    assignments.append(
                        {
                            "NOPOL": nopol,
                            "Jenis": fleet["JENIS KENDARAAN"],
                            "Sopir": fleet["SOPIR"],
                            "Total_Muatan": round(current_load, 3),
                            "Kapasitas": cap,
                            "Efisiensi": f"{(current_load/cap)*100:.1f}%",
                            "Order_IDs": ", ".join(assigned_orders),
                        }
                    )

            st.subheader("💡 Hasil Rekomendasi Alokasi Kiriman:")
            rec_df = pd.DataFrame(assignments)
            st.dataframe(rec_df, use_container_width=True)

            if st.button("✅ Terapkan Rekomendasi Ini"):
                for row in assignments:
                    order_ids = [
                        x.strip() for x in row["Order_IDs"].split(",")
                    ]
                    st.session_state.orders.loc[
                        st.session_state.orders["Order_ID"].isin(order_ids),
                        "Status",
                    ] = "Planned"
                    st.session_state.orders.loc[
                        st.session_state.orders["Order_ID"].isin(order_ids),
                        "Assigned_Nopol",
                    ] = row["NOPOL"]
                st.success("Rekomendasi berhasil diterapkan!")
                st.rerun()

# ---------------------------------------------------------
# MENU 5: MONITORING & SURAT JALAN
# ---------------------------------------------------------
elif menu == "📋 Monitoring & Surat Jalan":
    st.title("📋 Monitoring Kiriman & Cetak Manifest")

    planned_df = st.session_state.orders[
        st.session_state.orders["Status"] == "Planned"
    ]

    if planned_df.empty:
        st.info("Belum ada kiriman yang direncanakan.")
    else:
        selected_nopol_view = st.selectbox(
            "Pilih Armada untuk Mencetak Surat Jalan / Manifest:",
            options=planned_df["Assigned_Nopol"].unique(),
        )

        manifest_data = planned_df[
            planned_df["Assigned_Nopol"] == selected_nopol_view
        ]
        fleet_detail = df_fleet[
            df_fleet["NOPOL"] == selected_nopol_view
        ].iloc[0]

        st.markdown(f"### 📄 MANIFEST KIRIMAN / SURAT JALAN")
        st.write(
            f"**No. Polisi:** `{fleet_detail['NOPOL']}` | **Kendaraan:** `{fleet_detail['JENIS KENDARAAN']}`"
        )
        st.write(
            f"**Driver:** `{fleet_detail['SOPIR']}` | **Kernet:** `{fleet_detail['KERNET']}`"
        )
        st.write(
            f"**Total Tonase:** `{manifest_data['Total_Tonase'].sum():.3f} / {fleet_detail['KAPASITAS (TON)']} Ton`"
        )

        st.table(
            manifest_data[
                [
                    "Order_ID",
                    "Customer",
                    "Alamat",
                    "Nama_Barang",
                    "Qty",
                    "Total_Tonase",
                ]
            ]
        )

        # Download button
        csv = manifest_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Surat Jalan (CSV/Excel)",
            data=csv,
            file_name=f"Surat_Jalan_{selected_nopol_view}.csv",
            mime="text/csv",
        )