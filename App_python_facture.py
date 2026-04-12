import streamlit as st
import re
import pandas as pd
import pdfplumber
from collections import namedtuple

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


# =========================
# 💶 FORMAT EURO
# =========================
def format_euro(x):
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


# =========================
# 📄 PDF GENERATION
# =========================
def create_pdf_from_selection(df_final, numero_facture, date_facture, date_echeance):

    file_name = "facture_generee.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    logo = Image("logo.png", width=60, height=80)

    emetteur = Table([
        [Paragraph("<b>VIZO-VINO</b>", styles["Normal"])],
        [Paragraph("51 rue d'Orléans", styles["Normal"])],
        [Paragraph("45130 MEUNG SUR LOIRE", styles["Normal"])],
        [Paragraph("RCS Orléans 909 286 817 00012", styles["Normal"])],
        [Paragraph("APE 4725Z", styles["Normal"])],
        [Paragraph("TVA : FR79909286817", styles["Normal"])],
        [Paragraph("E-mail : meungsurloire.intercaves@gmail.com", styles["Normal"])],
    ])

    client = Table([
        [Paragraph("<b>FURI Cave de la Vallée</b>", styles["Normal"])],
        [Paragraph("327 RN 20", styles["Normal"])],
        [Paragraph("45770 SARAN", styles["Normal"])],
    ])

    titre = Paragraph("<b>FACTURE</b>", styles["Title"])

    header_table = Table([
        [logo, "", titre],
        [emetteur, "", client],
    ], colWidths=[200, 70, 220])

    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # =========================
    # INFOS FACTURE
    # =========================
    info_table = Table([
        ["Numéro", "Date"],
        [numero_facture, date_facture]
    ], colWidths=[200, 200])

    info_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # =========================
    # ARTICLES TABLE (AVEC €)
    # =========================
    df_articles = df_final.iloc[:-3]

    data = [df_articles.columns.tolist()] + [
        [
            row["Article"],
            row["Description"],
            row["Quantité"],
            format_euro(row["Prix Unitaire (€)"]),
            format_euro(row["Total (€)"]),
        ]
        for _, row in df_articles.iterrows()
    ]

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elements.append(table)

    # =========================
    # TOTAUX (AVEC €)
    # =========================
    total_ht = df_final.iloc[-3]["Total (€)"]
    tva = df_final.iloc[-2]["Total (€)"]
    total_ttc = df_final.iloc[-1]["Total (€)"]

    elements.append(Spacer(1, 20))

    totals_table = Table([
        ["Total HT", format_euro(total_ht)],
        ["TVA (20%)", format_euro(tva)],
        ["Total TTC", format_euro(total_ttc)],
    ], colWidths=[300, 100])

    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
    ]))

    elements.append(totals_table)

    elements.append(Spacer(1, 25))

    # =========================
    # 💳 BLOC IBAN / PAIEMENT
    # =========================
    paiement_table = Table([
        ["Règlement par chèque ou virement"],
        ["IBAN : FR76 1480 6000 2172 0423 3517 873"],
        ["BIC : AGRIFRPP848"],
    ], colWidths=[400])

    paiement_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(paiement_table)

    elements.append(Spacer(1, 15))

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(f"<b>Échéance le {date_echeance}</b>", styles["Normal"])
    )

    elements.append(Spacer(1, 10))

    # =========================
    # 📜 TEXTE LÉGAL
    # =========================
    texte_legal = """
    Le transfert de propriété est différé jusqu'au paiement intégral des marchandises livrées. (loi 80335 du 12/05/1980 
    et 85-98 du 25.01.1985) En cas de paiement effectué par le client avant l'échéance convenue, celui-ci ne pourra bénéficier 
    d'aucun escompte. A défaut de règlement de la facture à l'échéance convenue, toute somme restant due sera majorée d'une 
    pénalité de retard au taux de 1,5% par mois.
    """

    elements.append(Paragraph(texte_legal, styles["Normal"]))

    elements.append(Spacer(1, 10))

    doc.build(elements)
    return file_name


# =========================
# 🚀 STREAMLIT APP
# =========================
st.title("📄 Traitement de facture LMDW")

presta = namedtuple("Prestation", "Numéro_Article Description Quantité Prix_Total")

pdf_file = st.file_uploader("Uploader le PDF", type="pdf")

if pdf_file:

    start_page = st.number_input("📄 Page de départ", min_value=1, value=1)
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

    articles = []

    for ligne in text.splitlines():
        match = pres_re.search(ligne)
        if match:
            articles.append(presta(
                match.group(1),
                match.group(2),
                match.group(3),
                match.group(4)
            ))

    df = pd.DataFrame(articles)

    if not df.empty:

        df["Quantité"] = df["Quantité"].astype(int)
        df["Prix_Total"] = df["Prix_Total"].str.replace(",", ".").astype(float)

        df_grouped = df.groupby(
            ["Numéro_Article", "Description"], as_index=False
        ).agg({"Quantité": "sum", "Prix_Total": "sum"})

        st.dataframe(df_grouped)

        selected = st.multiselect(
            "Choisir les articles",
            df_grouped["Description"].tolist()
        )

        df_selection = df_grouped[df_grouped["Description"].isin(selected)].copy()

        numero_facture = st.text_input("🧾 Numéro facture")
        date_facture = st.date_input("📅 Date")
        date_echeance = st.date_input("⏳ Date d'échéance")

        if not df_selection.empty:

            quantites = []

            st.write("### 🛒 Saisie des quantités")

            for i, row in df_selection.iterrows():
                col1, col2, col3 = st.columns([2, 6, 2])

                with col1:
                    st.write(f"**{row['Numéro_Article']}**")

                with col2:
                    st.write(row["Description"])

                with col3:
                    q = st.number_input(
                        "Qté",
                        min_value=0.0,
                        step=1.0,
                        key=f"qte_{i}",
                        label_visibility="collapsed"
                    )

                quantites.append(q)

            df_selection["Quantité Saran"] = quantites

            df_selection["Prix Unitaire (€)"] = (
                df_selection["Prix_Total"] / df_selection["Quantité"]
            ).round(2)

            df_selection["Total (€)"] = (
                df_selection["Prix Unitaire (€)"] * df_selection["Quantité Saran"]
            ).round(2)

            df_selection = df_selection[
                ["Numéro_Article", "Description", "Quantité Saran",
                 "Prix Unitaire (€)", "Total (€)"]
            ].rename(columns={
                "Numéro_Article": "Article",
                "Quantité Saran": "Quantité"
            })

            total_ht = df_selection["Total (€)"].sum()
            tva = round(total_ht * 0.2, 2)
            total_ttc = round(total_ht + tva, 2)

            df_totaux = pd.DataFrame([
                {"Article": "", "Description": "Total HT", "Total (€)": total_ht},
                {"Article": "", "Description": "TVA 20%", "Total (€)": tva},
                {"Article": "", "Description": "Total TTC", "Total (€)": total_ttc},
            ])

            df_final = pd.concat([df_selection, df_totaux], ignore_index=True)

            st.subheader("Prévisualisation")
            st.dataframe(df_final)

            if st.button("Générer PDF"):

                pdf_file_name = create_pdf_from_selection(
                    df_final,
                    numero_facture,
                    date_facture.strftime("%d/%m/%Y"),
                    date_echeance.strftime("%d/%m/%Y")
                )

                with open(pdf_file_name, "rb") as f:
                    st.download_button(
                        "Télécharger PDF",
                        data=f.read(),
                        file_name=pdf_file_name,
                        mime="application/pdf"
                    )