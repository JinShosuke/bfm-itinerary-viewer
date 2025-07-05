import streamlit as st
import json
import pandas as pd
from io import BytesIO

# Load your BFM parsed JSON file
with open("bfm_parsed_output.json", "r") as f:
    itineraries = json.load(f)

st.set_page_config(page_title="BFM Viewer", layout="wide")
st.title("✈️ BFM Itinerary Viewer")

selected_itin = st.selectbox("Select Itinerary", [f"Itinerary {itin['itineraryId']}" for itin in itineraries])
itin = next(i for i in itineraries if f"Itinerary {i['itineraryId']}" == selected_itin)

st.header(f"🧭 Itinerary ID: {itin['itineraryId']}")
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

# Downloadable CSV/Excel exports
def to_excel(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for name, df in df_dict.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output

if st.button("📥 Download All as Excel"):
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
