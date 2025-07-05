import streamlit as st
import json
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Load your BFM parsed JSON file
try:
    with open("bfm_parsed_output.json", "r") as f:
        itineraries = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    st.error(f"Error loading JSON file: {e}")
    st.stop()

st.set_page_config(page_title="BFM Viewer", layout="wide")
st.title("✈️ BFM Itinerary Viewer")

# === FILTERING ===
passenger_types = list({p["passengerType"] for i in itineraries for p in i["penalties"]})
routes = [
    f"{i['segments']['Outbound'][0]['origin']} → {i['segments']['Outbound'][-1]['destination']}"
    for i in itineraries if i["segments"].get("Outbound")
]
dates = [
    i["segments"]["Outbound"][0]["departureDate"]
    for i in itineraries if i["segments"].get("Outbound")
]

st.sidebar.header("🔍 Filters")
selected_passenger = st.sidebar.multiselect("Passenger Type", passenger_types)
selected_route = st.sidebar.multiselect("Route", list(set(routes)))
selected_dates = st.sidebar.multiselect("Departure Date", list(set(dates)))

filtered_itins = [
    i for i in itineraries
    if (not selected_passenger or any(p["passengerType"] in selected_passenger for p in i["penalties"]))
    and (not selected_route or f"{i['segments']['Outbound'][0]['origin']} → {i['segments']['Outbound'][-1]['destination']}" in selected_route)
    and (not selected_dates or i['segments']['Outbound'][0]["departureDate"] in selected_dates)
]

if not filtered_itins:
    st.warning("No itineraries match your filter.")
    st.stop()

# === DARK MODE TOGGLE ===
dark_mode = st.sidebar.toggle("🌗 Dark Mode")
if dark_mode:
    st.markdown(
        """
        <style>
        body { background-color: #111; color: white; }
        .stDataFrame { background-color: #222 !important; color: white; }
        </style>
        """,
        unsafe_allow_html=True
    )

# === MULTI ITINERARY COMPARISON ===
selected_itins = st.multiselect("Select Itineraries to View", [f"Itinerary {i['itineraryId']}" for i in filtered_itins])

for label in selected_itins:
    itin = next(i for i in filtered_itins if f"Itinerary {i['itineraryId']}" == label)

    st.header(f"🧭 {label}")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📍 Segments - Outbound")
        st.dataframe(pd.DataFrame(itin["segments"].get("Outbound", [])))

        st.subheader("🧳 Baggage - Outbound")
        st.dataframe(pd.DataFrame(itin["baggage"].get("Outbound", [])))

        st.subheader("📑 Segment Details - Outbound")
        st.dataframe(pd.DataFrame(itin["segmentDetails"].get("Outbound", [])))

    with col2:
        st.subheader("📍 Segments - Inbound")
        st.dataframe(pd.DataFrame(itin["segments"].get("Inbound", [])))

        st.subheader("🧳 Baggage - Inbound")
        st.dataframe(pd.DataFrame(itin["baggage"].get("Inbound", [])))

        st.subheader("📑 Segment Details - Inbound")
        st.dataframe(pd.DataFrame(itin["segmentDetails"].get("Inbound", [])))

    st.subheader("💰 Fare Info")
    st.dataframe(pd.DataFrame(itin["fareInfo"]))

    st.subheader("💸 Taxes")
    st.dataframe(pd.DataFrame(itin["taxes"]))

    st.subheader("🚫 Penalties (Per Passenger & Direction)")
    for passenger in itin["penalties"]:
        st.markdown(f"**👤 Passenger Type: {passenger['passengerType']}**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Outbound:**")
            st.dataframe(pd.DataFrame(passenger["penaltiesByDirection"].get("Outbound", [])))
        with col2:
            st.markdown("**Inbound:**")
            st.dataframe(pd.DataFrame(passenger["penaltiesByDirection"].get("Inbound", [])))

    def to_excel(df_dict):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for name, df in df_dict.items():
                df.to_excel(writer, sheet_name=name[:31], index=False)
        output.seek(0)
        return output

    if st.button(f"📥 Download Excel for {itin['itineraryId']}"):
        data_to_export = {
            "Segments_Outbound": pd.DataFrame(itin["segments"].get("Outbound", [])),
            "Segments_Inbound": pd.DataFrame(itin["segments"].get("Inbound", [])),
            "Baggage_Outbound": pd.DataFrame(itin["baggage"].get("Outbound", [])),
            "Baggage_Inbound": pd.DataFrame(itin["baggage"].get("Inbound", [])),
            "SegmentDetails_Outbound": pd.DataFrame(itin["segmentDetails"].get("Outbound", [])),
            "SegmentDetails_Inbound": pd.DataFrame(itin["segmentDetails"].get("Inbound", [])),
            "FareInfo": pd.DataFrame(itin["fareInfo"]),
            "Taxes": pd.DataFrame(itin["taxes"])
        }
        for pax in itin["penalties"]:
            outbound_df = pd.DataFrame(pax["penaltiesByDirection"].get("Outbound", []))
            inbound_df = pd.DataFrame(pax["penaltiesByDirection"].get("Inbound", []))
            data_to_export[f"Penalties_{pax['passengerType']}_Outbound"] = outbound_df
            data_to_export[f"Penalties_{pax['passengerType']}_Inbound"] = inbound_df

        excel_data = to_excel(data_to_export)
        st.download_button(
            label="Download Excel File",
            data=excel_data,
            file_name=f"itinerary_{itin['itineraryId']}_details.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def create_pdf(itin):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        elements = [Paragraph(f"Itinerary ID: {itin['itineraryId']}", styles["Title"])]
        for key in ["segments", "baggage", "segmentDetails"]:
            for direction in ["Outbound", "Inbound"]:
                df = pd.DataFrame(itin[key].get(direction, []))
                elements.append(Paragraph(f"{key.title()} - {direction}", styles["Heading2"]))
                elements.append(Paragraph(df.head(10).to_string(), styles["Code"]))
        doc.build(elements)
        buffer.seek(0)
        return buffer

    if st.button(f"📄 Export PDF for {itin['itineraryId']}"):
        pdf = create_pdf(itin)
        st.download_button("Download PDF", data=pdf, file_name=f"itinerary_{itin['itineraryId']}.pdf", mime="application/pdf")