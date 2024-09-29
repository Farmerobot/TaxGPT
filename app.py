import os
from openai import AzureOpenAI
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from xml.dom import minidom

app = Flask(__name__)

def load_system_prompt(prompt_file):
    """Read the system prompt from a file."""
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

def extract_non_nested_fields_to_dict(xsd_file):
    # Parse the XML schema file
    tree = ET.parse(xsd_file)
    root = tree.getroot()

    # Initialize an empty dictionary to store required field names with empty string values
    required_fields_dict = {}

    # Namespace used in XSD files
    ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}

    # Extract elements that do not have any <xs:element> children
    for element in root.findall(".//xs:element", ns):
        field_name = element.get("name")
        min_occurs = element.get("minOccurs")

        # Check if the element has children that are <xs:element>
        has_element_children = any(child.tag.endswith("element") for child in element.findall(".//*", ns))

        # Only add elements that do not have <xs:element> children
        if field_name and (min_occurs is None or min_occurs != "0") and not has_element_children:
            required_fields_dict[field_name] = ""

    return required_fields_dict

def create_xml_from_dict(field_dict, output_xml_file):
    # Create root element for the XML file
    deklaracja = ET.Element("Deklaracja")

    # Create Naglowek section
    naglowek = ET.SubElement(deklaracja, "Naglowek")
    ET.SubElement(naglowek, "KodFormularza", {
        "kodSystemowy": "PCC-3 (6)",
        "kodPodatku": "PCC",
        "rodzajZobowiazania": "Z",
        "wersjaSchemy": "1-0E"
    }).text = field_dict.get("KodFormularza", "")
    ET.SubElement(naglowek, "WariantFormularza").text = field_dict.get("WariantFormularza", "")
    ET.SubElement(naglowek, "CelZlozenia", {"poz": "P_6"}).text = field_dict.get("CelZlozenia", "")
    ET.SubElement(naglowek, "Data", {"poz": "P_4"}).text = field_dict.get("Data", "")
    ET.SubElement(naglowek, "KodUrzedu").text = field_dict.get("KodUrzedu", "")

    # Create Podmiot1 section
    podmiot1 = ET.SubElement(deklaracja, "Podmiot1", {"rola": "Podatnik"})
    osoba_fizyczna = ET.SubElement(podmiot1, "OsobaFizyczna")
    ET.SubElement(osoba_fizyczna, "NIP").text = field_dict.get("NIP", "")
    ET.SubElement(osoba_fizyczna, "ImiePierwsze").text = field_dict.get("ImiePierwsze", "")
    ET.SubElement(osoba_fizyczna, "Nazwisko").text = field_dict.get("Nazwisko", "")
    ET.SubElement(osoba_fizyczna, "DataUrodzenia").text = field_dict.get("DataUrodzenia", "")
    ET.SubElement(osoba_fizyczna, "ImieOjca").text = field_dict.get("ImieOjca", "")
    ET.SubElement(osoba_fizyczna, "ImieMatki").text = field_dict.get("ImieMatki", "")

    # Create AdresZamieszkaniaSiedziby section
    adres_zamieszkania = ET.SubElement(podmiot1, "AdresZamieszkaniaSiedziby", {"rodzajAdresu": "RAD"})
    adres_pol = ET.SubElement(adres_zamieszkania, "AdresPol")
    ET.SubElement(adres_pol, "KodKraju").text = field_dict.get("KodKraju", "PL")
    ET.SubElement(adres_pol, "Wojewodztwo").text = field_dict.get("Wojewodztwo", "")
    ET.SubElement(adres_pol, "Powiat").text = field_dict.get("Powiat", "")
    ET.SubElement(adres_pol, "Gmina").text = field_dict.get("Gmina", "")
    ET.SubElement(adres_pol, "Ulica").text = field_dict.get("Ulica", "")
    ET.SubElement(adres_pol, "NrDomu").text = field_dict.get("NrDomu", "")
    ET.SubElement(adres_pol, "NrLokalu").text = field_dict.get("NrLokalu", "")
    ET.SubElement(adres_pol, "Miejscowosc").text = field_dict.get("Miejscowosc", "")
    ET.SubElement(adres_pol, "KodPocztowy").text = field_dict.get("KodPocztowy", "")

    # Create PozycjeSzczegolowe section
    pozycje_szczegolowe = ET.SubElement(deklaracja, "PozycjeSzczegolowe")
    for field, value in field_dict.items():
        if field not in ["NIP", "ImiePierwsze", "Nazwisko", "DataUrodzenia", "ImieOjca", "ImieMatki", "KodKraju", "Wojewodztwo", "Powiat", "Gmina", "Ulica", "NrDomu", "NrLokalu", "Miejscowosc", "KodPocztowy"]:
            ET.SubElement(pozycje_szczegolowe, field).text = value

    # Create Pouczenia section
    ET.SubElement(deklaracja, "Pouczenia").text = field_dict.get("Pouczenia", "")

    # Convert the tree to a string and prettify using minidom
    rough_string = ET.tostring(deklaracja, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

    # Write the prettified XML to the output file
    with open(output_xml_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_string)

    print("XML file created with populated required fields at:", output_xml_file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data['text']

    # Add user's message to messages
    messages.append({"text": user_message, "sender": "user"})

    # Read system prompt from prompt.txt
    system_prompt = load_system_prompt('prompt.txt')

    # Get response from Azure OpenAI using ChatCompletion
    try:
        response = client.chat.completions.create(model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=150)

        # Extract the assistant's response
        ai_response = response.choices[0].message.content.strip()
        messages.append({"text": ai_response, "sender": "bot"})
    except Exception as e:
        ai_response = "Sorry, there was an error processing your request: " + str(e)
        messages.append({"text": ai_response, "sender": "bot"})

    return jsonify(success=True)

@app.route('/generate_xml', methods=['GET'])
def generate_xml():
    # Create the XML file using the dictionary values
    create_xml_from_dict(field_dict, output_xml_file)

    # Send the generated XML file as a download
    return send_file(output_xml_file, as_attachment=True, download_name='output.xml')

if __name__ == "__main__":
    client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2023-03-15-preview")

    # Load environment variables from .env file
    load_dotenv()

    # In-memory storage for chat messages
    messages = [{"text": "W czym mogę pomóc?", "sender": "system"}]

    # Extract fields into a dictionary with empty values
    xsd_file = 'schema.xsd'  # Ensure this path is correct and accessible
    output_xml_file = 'output.xml'  # Temporary output XML file path

    # Create the dictionary from the XSD file
    field_dict = extract_non_nested_fields_to_dict(xsd_file)

    # Populate the dictionary with sample values (customize as needed)
    field_dict["KodFormularza"] = "PCC-3"
    field_dict["WariantFormularza"] = "6"
    field_dict["CelZlozenia"] = "1"
    field_dict["P_20"] = "1"
    field_dict["Pouczenia"] = "1"

    app.run(host='0.0.0.0', port=8000)
