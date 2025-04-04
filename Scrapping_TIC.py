from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
import time
import sqlite3
import re


def create_db(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id_doc TEXT PRIMARY KEY,
            description TEXT,
            year INTEGER,
            entidad TEXT,
            category TEXT,
            url_doc TEXT,
            text_doc TEXT
        )
        """
    )
    conn.commit()
    print("Conexión correcta: OK")


def save_on_db(cursor, data):
    cursor.execute(
        """
        INSERT OR IGNORE INTO documents (id_doc, description, year, entidad, category, url_doc, text_doc)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            data["id-doc"],
            data["description"],
            data["year"],
            data["entidad"],
            data["category"],
            data["url-doc"],
            data["text"],
        ),
    )


if __name__ == "__main__":

    # Ruta al controlador de ChromeDriver
    PATH = "chromedriver\chromedriver.exe"
    service = Service(PATH)
    driver = webdriver.Chrome(service=service)

    # Base de datos
    conn = sqlite3.connect("DB/normativa_tic.db")

    create_db(conn)
    cursor = conn.cursor()

    try:
        # Navegar a la página objetivo
        driver.get(
            "https://normograma.crcom.gov.co/crc/compilacion/normativa_sector_tic.html"
        )

        # Esperar a que el contenido dinámico se cargue
        wait = WebDriverWait(driver, 10)
        main_window = driver.current_window_handle
        secciones = driver.find_elements(
            By.CLASS_NAME,
            "opcion-nueva",
        )

        for seccion in secciones:
            try:
                # Encontrar el botón "Abrir" dentro de cada sección
                btn_abrir = seccion.find_element(
                    By.CLASS_NAME,
                    "contenedor-ver-mas-opcion-nueva",
                )
                category = seccion.find_element(By.CLASS_NAME, "id-tipo-documento").text
                print(f"-> Consultando {category} ...")

                # Hacer clic en el botón para expandir la sección
                driver.execute_script("arguments[0].click();", btn_abrir)
                time.sleep(1)  # Esperar a que cargue el contenido
                prev_pag_1 = driver.current_window_handle
                entidades = seccion.find_elements(By.CLASS_NAME, "opcion-entidad")

                for entidad in entidades:
                    name_entidad = entidad.find_element(
                        By.CLASS_NAME, "id-entidad"
                    ).text
                    print(f"--> Abriendo {name_entidad} ...")

                    href = entidad.find_element(By.TAG_NAME, "a").get_attribute("href")
                    driver.execute_script(f"window.open('{href}', '_blank');")
                    time.sleep(1)  # Esperar a que cargue el contenido
                    driver.switch_to.window(driver.window_handles[-1])
                    ### modificar para el filtro de decretos
                    exist_btn_years = bool(
                        driver.find_elements(By.CLASS_NAME, "boton-selector-year")
                    )
                    if exist_btn_years:
                        prev_pag_2 = driver.current_window_handle
                        btn_years = driver.find_element(
                            By.CLASS_NAME, "boton-selector-year"
                        )
                        btn_years.click()
                        time.sleep(1)
                        year_texts = btn_years.text.split("\n")
                        if year_texts[0] == "IR A AÑO":
                            year_texts = [year_texts[1]]
                        elif year_texts[0] == "FILTRAR POR AÑO":
                            year_texts = year_texts[1:]

                    else:
                        year_texts = ["2025"]

                    #####
                    for i, year_txt in enumerate(year_texts):
                        if not re.match(r"^\d{4}$", year_txt):
                            continue

                        if exist_btn_years:
                            selector = driver.find_element(
                                By.XPATH,
                                f"/html/body/div[1]/div/main/div/div/nav/form/div/div/div[1]/div/div[2]/div[{i+1}]",
                            )
                            driver.execute_script("arguments[0].click();", selector)
                            time.sleep(1)

                        years = driver.find_elements(By.CLASS_NAME, "opcion-year")
                        if not exist_btn_years:
                            prev_pag_2 = driver.current_window_handle

                        for year in years:
                            year_txt = year.find_element(
                                By.CLASS_NAME, "titulo-opcion-year"
                            ).text
                            print(f"---> Año: {year_txt}")
                            documentos = year.find_elements(
                                By.CLASS_NAME, "opcion-nueva"
                            )

                            for doc in documentos:
                                extracted_data = {}

                                doc_title = doc.find_element(
                                    By.CLASS_NAME, "id-documento"
                                ).text
                                print(f"----> Doc: {doc_title}")
                                doc_desc = doc.find_element(
                                    By.CLASS_NAME, "descripcion-documento"
                                ).text

                                href = doc.find_element(By.TAG_NAME, "a").get_attribute(
                                    "href"
                                )
                                driver.execute_script(
                                    f"window.open('{href}', '_blank');"
                                )
                                time.sleep(1)  # Esperar a que cargue el contenido
                                driver.switch_to.window(driver.window_handles[-1])
                                url = driver.current_url

                                # Leer documento
                                div_doc = driver.find_element(
                                    By.CLASS_NAME, "panel-documento"
                                )
                                text_elements = div_doc.find_elements(
                                    By.XPATH, ".//a | .//p"
                                )
                                text = [elem.text for elem in text_elements]
                                all_text = "\n".join(text)

                                extracted_data["id-doc"] = doc_title
                                extracted_data["description"] = doc_desc
                                extracted_data["year"] = year_txt
                                extracted_data["entidad"] = name_entidad
                                extracted_data["category"] = category
                                extracted_data["url-doc"] = url
                                extracted_data["text"] = all_text

                                save_on_db(cursor, extracted_data)
                                # Cerrar la nueva pestaña y volver a la original (opcional)
                                driver.close()
                                driver.switch_to.window(prev_pag_2)

                    driver.close()
                    driver.switch_to.window(prev_pag_1)

            except Exception as e:
                print(f"Error en la sección: {str(e)}")
    finally:
        # Cerrar el navegador
        conn.commit()
        conn.close()
        driver.quit()
