import streamlit as st
import re
import pandas as pd
import pdfplumber
from collections import namedtuple
import openpyxl
import base64


st.title("📄 Traitement de facture LMDW.")

presta = namedtuple("Prestation", "Numéro_Article Description Quantité Prix_Total")

# Upload du PDF
pdf_file = st.file_uploader("Uploader le PDF", type="pdf")

if pdf_file:

    start_page = st.number_input(
        "📄 Page de départ de l'annexe",
        min_value=1,
        value=5,
        step=1
    )

    start_index = start_page - 1

    text = ""
    with pdfplumber.open(pdf_file) as pdf:

        total_pages = len(pdf.pages)
        st.info(f"Le PDF contient {total_pages} pages")

        if start_index >= total_pages:
            st.error("⚠️ La page de départ dépasse le nombre de pages du PDF")
        else:
            for page in pdf.pages[start_index:]:
                text += page.extract_text()

    pres_re = re.compile(r"(^\d+\S*)\s(.+?)\s+(\d+)\s+0,\d+.*?(\d+,\d+|\d+)\s+\d+\s*$")

    Article = []

    for ligne in text.splitlines():
        match = pres_re.search(ligne)
        if match:
            num_art = match.group(1)
            desc = match.group(2)
            qté = match.group(3)
            prix_tot = match.group(4)

            Article.append(presta(num_art, desc, qté, prix_tot))

    df = pd.DataFrame(Article)

    if not df.empty:
        df["Quantité"] = df["Quantité"].astype(int)
        df["Prix_Total"] = df["Prix_Total"].str.replace(",", ".").astype(float)

        df_grouped = df.groupby(
            ["Numéro_Article", "Description"], as_index=False
        ).agg({"Quantité": "sum", "Prix_Total": "sum"})

        st.subheader("📊 Articles détectés")
        st.dataframe(df_grouped)

        # Sélection utilisateur
        st.subheader("🛒 Sélection des articles")

        articles = df_grouped["Numéro_Article"].astype(str).tolist()
        selected_articles = st.multiselect("Choisir les articles", articles)

        df_selection = df_grouped[df_grouped["Numéro_Article"].astype(str).isin(selected_articles)].copy()

        if not df_selection.empty:

            quantites = []

            st.write("### 🛒 Saisie des quantités")

            for i, row in df_selection.iterrows():
                col1, col2, col3 = st.columns([2, 5, 2])

                with col1:
                    st.write(f"**{row['Numéro_Article']}**")

                with col2:
                    st.write(row["Description"])

                with col3:
                    q = st.number_input(
                        "Qté",
                        min_value=0.0,
                        step=1.0,
                        key=f"qte_{i}"  # IMPORTANT sinon bug
                    )

                quantites.append(q)

            df_selection["Quantité Saran"] = quantites

            df_selection["Prix_Unitaire_Remisé"] = (
                df_selection["Prix_Total"] / df_selection["Quantité"].replace(0, None)
            ).round(2)

            df_selection["Prix_Total_Saran"] = (
                df_selection["Prix_Unitaire_Remisé"] * df_selection["Quantité Saran"]
            ).round(2)
            df_selection = df_selection[["Numéro_Article","Description","Quantité Saran","Prix_Unitaire_Remisé","Prix_Total_Saran"]]
            df_selection = df_selection.rename(columns={
                "Numéro_Article": "Article",
                "Quantité Saran": "Qté Saran",
                "Prix_Unitaire_Remisé": "Prix Unitaire (€)",
                "Prix_Total_Saran": "Total (€)"
            })

            st.subheader("✅ Résumé")
            st.dataframe(df_selection, hide_index=True)

            # Export Excel
            if st.button("📥 Télécharger Excel"):
                file_name = "selection.xlsx"
                df_selection.to_excel(file_name, index=False)

                with open(file_name, "rb") as f:
                    st.download_button(
                        label="Télécharger le fichier",
                        data=f,
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
