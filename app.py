import os
from openai import AzureOpenAI
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pydantic import BaseModel, Field, create_model, ValidationError
import json
from typing import Optional
import logging

class TaxGPT:
    def __init__(self):
        self.app = Flask(__name__)
        load_dotenv()
        self.client = AzureOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
                                  api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                                  api_version="2023-03-15-preview")
        self.messages = [{"text": "W czym mogę pomóc?", "sender": "system"}]
        self.xsd_file = 'schema.xsd'  # Ensure this path is correct and accessible
        self.output_xml_file = 'output.xml'  # Temporary output XML file path
        self.field_dict = self.extract_non_nested_fields_to_dict(self.xsd_file)
        self.temperature = 0.5
        self.DynamicFieldDict = create_model(
            'DynamicFieldDict',
            **{key: (Optional[str], Field()) for key in self.field_dict.keys()}
        )
        self.populate_sample_data()
        self.create_routes()

    def load_system_prompt(self, prompt_file):
        """Read the system prompt from a file."""
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def extract_non_nested_fields_to_dict(self, xsd_file):
        tree = ET.parse(xsd_file)
        root = tree.getroot()
        required_fields_dict = {}
        ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}

        for element in root.findall(".//xs:element", ns):
            field_name = element.get("name")
            min_occurs = element.get("minOccurs")
            has_element_children = any(child.tag.endswith("element") for child in element.findall(".//*", ns))

            if field_name and (min_occurs is None or min_occurs != "0") and not has_element_children:
                required_fields_dict[field_name] = ""

        return required_fields_dict

    def create_xml_from_dict(self, field_dict, output_xml_file):
        deklaracja = ET.Element("Deklaracja")
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

        podmiot1 = ET.SubElement(deklaracja, "Podmiot1", {"rola": "Podatnik"})
        osoba_fizyczna = ET.SubElement(podmiot1, "OsobaFizyczna")
        ET.SubElement(osoba_fizyczna, "NIP").text = field_dict.get("NIP", "")
        ET.SubElement(osoba_fizyczna, "ImiePierwsze").text = field_dict.get("ImiePierwsze", "")
        ET.SubElement(osoba_fizyczna, "Nazwisko").text = field_dict.get("Nazwisko", "")
        ET.SubElement(osoba_fizyczna, "DataUrodzenia").text = field_dict.get("DataUrodzenia", "")
        ET.SubElement(osoba_fizyczna, "ImieOjca").text = field_dict.get("ImieOjca", "")
        ET.SubElement(osoba_fizyczna, "ImieMatki").text = field_dict.get("ImieMatki", "")

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

        pozycje_szczegolowe = ET.SubElement(deklaracja, "PozycjeSzczegolowe")
        for field, value in field_dict.items():
            if field.startswith("P_"):
                ET.SubElement(pozycje_szczegolowe, field).text = value

        ET.SubElement(deklaracja, "Pouczenia").text = field_dict.get("Pouczenia", "")
        rough_string = ET.tostring(deklaracja, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml_as_string = reparsed.toprettyxml(indent="  ")

        with open(output_xml_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml_as_string)

        print("XML file created with populated required fields at:", output_xml_file)

    def populate_sample_data(self):
        self.field_dict["KodFormularza"] = "PCC-3"
        self.field_dict["WariantFormularza"] = "6"
        self.field_dict["CelZlozenia"] = "1"
        self.field_dict["P_20"] = "1"
        self.field_dict["Pouczenia"] = "1"
        self.field_dict["P_62"] = "1"

    def validate_dict(self, response_dict):
        from datetime import datetime

        # Validate "DATA DOKONANIA CZYNNOŚCI" (P4)
        if 'Data' in response_dict and response_dict['Data']:
            try:
                p4_date = datetime.strptime(response_dict['Data'], '%Y-%m-%d')
                min_date = datetime.strptime('2024-01-01', '%Y-%m-%d')
                if p4_date < min_date:
                    response_dict['Data'] = ""
            except ValueError:
                response_dict['Data'] = ""

        # Validate "CEL ZŁOŻENIA DEKLARACJI" (P6)
        if 'CelZlozenia' in response_dict:
            if response_dict['CelZlozenia'] != "1":
                response_dict['CelZlozenia'] = ""

        # Validate "PODMIOT SKŁADAJĄCY DEKLARACJĘ" (P7)
        if 'P7' in response_dict:
            if response_dict['P7'] not in ["1", "5"]:
                response_dict['P7'] = ""

        # Validate "PRZEDMIOT OPODATKOWANIA" (P20)
        if 'P20' in response_dict:
            if response_dict['P20'] != "1":
                response_dict['P20'] = ""

        # Validate "MIEJSCE POŁOŻENIA RZECZY LUB WYKONYWANIA PRAWA MAJĄTKOWEGO" (P21)
        if 'P21' in response_dict:
            if response_dict['P21'] not in ["0", "1", "2"]:
                response_dict['P21'] = ""

        # Validate "MIEJSCE DOKONANIA CZYNNOŚCI CYWILNOPRAWNEJ" (P22)
        if 'P22' in response_dict:
            if response_dict['P22'] not in ["0", "1", "2"]:
                response_dict['P22'] = ""

        # Validate "PODSTAWA OPODATKOWANIA DLA UMOWY SPRZEDAŻY" (P26)
        if 'P26' in response_dict:
            try:
                p26_value = float(response_dict['P26'])
                if p26_value < 1000:
                    response_dict['P26'] = ""
            except ValueError:
                response_dict['P26'] = ""

        # Validate "LICZBA DOŁĄCZONYCH ZAŁĄCZNIKÓW PCC-3/A" (P62)
        if 'P62' in response_dict and 'P7' in response_dict:
            try:
                p62_value = int(response_dict['P62'])
                if response_dict['P7'] == "1" and p62_value <= 0:
                    response_dict['P62'] = ""
                elif response_dict['P7'] != "1" and p62_value != 0:
                    response_dict['P62'] = ""
            except ValueError:
                response_dict['P62'] = ""

        return response_dict

    def create_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/get_messages', methods=['GET'])
        def get_messages():
            return jsonify(self.messages)

        @self.app.route('/send_message', methods=['POST'])
        def send_message():
            data = request.get_json()
            user_message = data['text']
            self.messages.append({"text": user_message, "sender": "user"})

            system_prompt = self.load_system_prompt('prompt.txt')
            empty_keys = [key for key, value in self.field_dict.items() if value == ""]
            extraction_prompt = "Puste pole to: " + ", ".join(empty_keys[0]) + ".\nOraz to co napisał użytkownik: " + f"{self.messages[-1]}\n" + "\n"
            extraction_prompt += self.load_system_prompt('prompt1.txt')

            try:
                response2 = self.client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": self.load_system_prompt('prompt2.txt') + f"\n\nPoprzednie wiadomości: {self.messages}"}],
                    response_format=self.DynamicFieldDict,
                    temperature=self.temperature
                )
                parsed_response2 = response2.choices[0].message.parsed
                response_dict2 = parsed_response2.dict()

                validated_dict = self.validate_dict(response_dict2)

                for key, value in validated_dict.items():
                    if value:
                        self.field_dict[key] = value
                        print(f"Field '{key}' populated with value: {value}")
            except Exception as e:
                ai_response = "Sorry, there was an error processing your request: " + str(e)
                # self.messages.append({"text": ai_response, "sender": "bot"})
                print(ai_response)

            # Validate the prompt
            validation_prompt = self.load_system_prompt('zalacznik3.txt')
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": extraction_prompt + user_message}],
                    max_tokens=200,
                    temperature=self.temperature
                )
                if response:
                    error = response.choices[0].message.content.strip() + "\n"
                else:
                    error = ""
            except Exception as e:
                print(response)

            empty_keys = [key for key, value in self.field_dict.items() if value == ""]
            not_empty_keys = [(key, value) for key, value in self.field_dict.items() if value != ""]
            print("Empty keys:", empty_keys)
            print("Not empty keys:", not_empty_keys)
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": f"{error}Oto puste pola: " + ", ".join(empty_keys) + self.load_system_prompt('prompt2.txt') + f"Oto poprzednia wiadomość: {self.messages}\n"}],
                    max_tokens=200,
                    temperature=self.temperature
                )

                ai_response = response.choices[0].message.content.strip()
                self.messages.append({"text": ai_response, "sender": "bot"})
            except Exception as e:
                ai_response = "Sorry, there was an error processing your request: " + str(e)
                # self.messages.append({"text": ai_response, "sender": "bot"})
                print(ai_response)

            return jsonify(success=True)

        @self.app.route('/generate_xml', methods=['GET'])
        def generate_xml():
            self.create_xml_from_dict(self.field_dict, self.output_xml_file)
            return send_file(self.output_xml_file, as_attachment=True, download_name='output.xml')

        @self.app.route('/generate_history', methods=['GET'])
        def generate_history():
            output_history_file = 'output_history.json'
            with open(output_history_file, 'w', encoding='utf-8') as f:
                f.write(f"{self.messages}")
            return send_file(output_history_file, as_attachment=True, download_name='output.json')

    def run(self):
        self.app.run()

tax_app = TaxGPT()
app = tax_app.app

if __name__ == "__main__":
    # Disable Flask logs by setting the logger level to ERROR
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    tax_app.run()