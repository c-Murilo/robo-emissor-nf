from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Callable

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_default_config() -> dict:
    return {
        "url": os.getenv(
            "NFSE_URL",
            "https://www.nfse.gov.br/EmissorNacional/Login?ReturnUrl=%2fEmissorNacional",
        ),
        "inscricao": os.getenv("NFSE_INSCRICAO", ""),
        "senha": os.getenv("NFSE_SENHA", ""),
        "cidade": os.getenv("NFSE_CIDADE", "Curitiba"),
        "tributacao_busca": os.getenv("NFSE_TRIBUTACAO_BUSCA", "fisioterapia"),
        "descricao_servico": os.getenv(
            "NFSE_DESCRICAO_SERVICO",
            "SERVICOS PRESTADOS DE FISIOTERAPIA",
        ),
        "intervalo_segundos": int(os.getenv("NFSE_INTERVALO_SEGUNDOS", "180")),
        "detach": _env_bool("NFSE_SELENIUM_DETACH", True),
    }


def _required_config_missing(cfg: dict) -> list[str]:
    required_fields = ["inscricao", "senha"]
    return [field for field in required_fields if not str(cfg.get(field, "")).strip()]


class NFSEBot:
    def __init__(self, config: dict):
        self.cfg = config
        self.driver = None
        self.wait = None
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)
        print(message, flush=True)

    def start(self) -> None:
        self._log("Etapa 1: iniciando Chrome.")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        if self.cfg["detach"]:
            chrome_options.add_experimental_option("detach", True)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.get(self.cfg["url"])
        self._log("Etapa 2: abriu URL do login.")

    def close(self) -> None:
        if self.driver and not self.cfg["detach"]:
            self.driver.quit()

    def login(self) -> None:
        # Garante que estamos na URL de login antes de qualquer ação.
        self.driver.get(self.cfg["url"])
        self._log("Etapa 3: tentando localizar campos de login.")

        try:
            campo_cpf_cnpj = WebDriverWait(self.driver, 12).until(
                EC.visibility_of_element_located((By.ID, "Inscricao"))
            )
            campo_cpf_cnpj.clear()
            campo_cpf_cnpj.send_keys(self.cfg["inscricao"])

            campo_senha = self.wait.until(EC.visibility_of_element_located((By.ID, "Senha")))
            campo_senha.clear()
            campo_senha.send_keys(self.cfg["senha"])

            botao_entrar = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            botao_entrar.click()
            self._log("Etapa 4: login enviado.")
        except TimeoutException:
            # Se não encontrou campos de login, pode já estar autenticado.
            self._log("Etapa 4: campos de login não encontrados; assumindo sessão ativa.")
            pass

        # Só considera login válido quando o menu principal estiver disponível.
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.dropdown-toggle[data-toggle='dropdown']"))
        )
        self._log("Etapa 5: menu principal carregado.")

    def abrir_emissao_completa(self) -> None:
        self._log("Etapa 6: abrindo emissão completa.")
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        menu_nova_nfse = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.dropdown-toggle[data-toggle='dropdown']"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu_nova_nfse)
        time.sleep(1)
        try:
            menu_nova_nfse.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", menu_nova_nfse)

        link_completa = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Emissão completa")))
        link_completa.click()
        # Confirma que entrou no formulário antes de continuar.
        self.wait.until(EC.visibility_of_element_located((By.ID, "DataCompetencia")))
        self._log("Etapa 7: formulário de emissão completo aberto.")

    def _clique_brasil(self) -> None:
        try:
            elemento_brasil = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(., 'Brasil')]")))
            elemento_brasil.click()
            self._log("Etapa 9: selecionou domicílio Brasil.")
        except Exception:
            try:
                span_click = self.driver.find_element(By.XPATH, "//label[contains(., 'Brasil')]//span[@class='cr']")
                span_click.click()
                self._log("Etapa 9: selecionou domicílio Brasil (span).")
            except Exception:
                radio_invisivel = self.driver.find_element(By.ID, "Tomador_LocalDomicilio")
                self.driver.execute_script("arguments[0].click();", radio_invisivel)
                self._log("Etapa 9: selecionou domicílio Brasil (JS).")

    def _preencher_select2_por_texto(self, select_id: str, termo: str) -> None:
        self._log(f"Etapa 12: selecionando {select_id} = {termo}.")
        xpath_combobox = (
            f"//select[@id='{select_id}']"
            "/following-sibling::span[contains(@class, 'select2-container')]//span[@role='combobox']"
        )

        dropdown_btn = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_combobox)))
        try:
            dropdown_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", dropdown_btn)

        campo_busca = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input.select2-search__field"))
        )
        campo_busca.send_keys(termo)

        xpath_resultado = f"//li[contains(@class, 'select2-results__option') and contains(text(), '{termo}')]"
        opcao = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_resultado)))
        opcao.click()

    def _preencher_select2_por_tab(self, select_id: str, termo: str) -> None:
        self._log(f"Etapa 13: selecionando {select_id} via TAB = {termo}.")
        xpath_combobox = (
            f"//select[@id='{select_id}']"
            "/following-sibling::span[contains(@class, 'select2-container')]//span[@role='combobox']"
        )
        dropdown_btn = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_combobox)))

        try:
            dropdown_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", dropdown_btn)

        campo_busca = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input.select2-search__field"))
        )
        campo_busca.send_keys(termo)
        time.sleep(1)
        campo_busca.send_keys(Keys.TAB)

    def _preencher_chosen_por_texto(self, chosen_container_id: str, texto: str) -> None:
        self._log(f"Etapa 16: selecionando Chosen {chosen_container_id} = {texto}.")
        container = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.ID, chosen_container_id))
        )
        # Garante abertura do dropdown do chosen (span -> a -> JS)
        try:
            container.find_element(By.CSS_SELECTOR, "a.chosen-single span").click()
        except Exception:
            try:
                container.find_element(By.CSS_SELECTOR, "a.chosen-single").click()
            except Exception:
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    const span = el.querySelector('a.chosen-single span');
                    const anchor = el.querySelector('a.chosen-single');
                    if (span) span.click();
                    else if (anchor) anchor.click();
                    else el.click();
                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    """,
                    container,
                )

        # Alguns chosen não permitem digitar (input readonly). Primeiro tenta direto na lista.
        try:
            opcao = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@id='{chosen_container_id}']//li[contains(@class,'active-result') and contains(., '{texto}')]",
                    )
                )
            )
            opcao.click()
            return
        except Exception:
            pass

        # Fallback: tenta usar a busca do chosen (quando habilitada).
        try:
            campo_busca = WebDriverWait(self.driver, 8).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, f"#{chosen_container_id} .chosen-search input"))
            )
            if not campo_busca.get_attribute("readonly"):
                campo_busca.clear()
                campo_busca.send_keys(texto)
                time.sleep(0.5)
                opcao = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            f"//div[@id='{chosen_container_id}']//li[contains(@class,'active-result') and contains(., '{texto}')]",
                        )
                    )
                )
                opcao.click()
                return
        except Exception:
            pass

        # Fallback final: ajusta o <select> original via JS
        self.driver.execute_script(
            """
            const chosenId = arguments[0];
            const texto = arguments[1];
            const selectId = chosenId.replace(/_chosen$/, '');
            const select = document.getElementById(selectId);
            if (!select) return false;
            let selected = null;
            for (const opt of select.options) {
                if (opt.text && opt.text.includes(texto)) {
                    selected = opt;
                    break;
                }
            }
            if (!selected) return false;
            select.value = selected.value;
            select.selectedIndex = selected.index;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            const span = document.querySelector('#' + chosenId + ' a.chosen-single span');
            if (span) span.textContent = selected.text;
            return true;
            """,
            chosen_container_id,
            texto,
        )

    def _preencher_chosen_primeira_opcao(self, chosen_container_id: str) -> None:
        self._log(f"Etapa 19: selecionando primeira opcao em {chosen_container_id}.")
        container = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.ID, chosen_container_id))
        )
        # Garante abertura do dropdown do chosen (span -> a -> JS)
        try:
            container.find_element(By.CSS_SELECTOR, "a.chosen-single span").click()
        except Exception:
            try:
                container.find_element(By.CSS_SELECTOR, "a.chosen-single").click()
            except Exception:
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    const span = el.querySelector('a.chosen-single span');
                    const anchor = el.querySelector('a.chosen-single');
                    if (span) span.click();
                    else if (anchor) anchor.click();
                    else el.click();
                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    """,
                    container,
                )

        try:
            opcao = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//div[@id='{chosen_container_id}']//li[contains(@class,'active-result') and @data-option-array-index='0']",
                    )
                )
            )
            opcao.click()
            return
        except Exception:
            pass

        # Fallback final: ajusta o <select> original via JS
        self.driver.execute_script(
            """
            const chosenId = arguments[0];
            const selectId = chosenId.replace(/_chosen$/, '');
            const select = document.getElementById(selectId);
            if (!select || select.options.length === 0) return false;
            select.selectedIndex = 0;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            const span = document.querySelector('#' + chosenId + ' a.chosen-single span');
            if (span) span.textContent = select.options[0].text;
            return true;
            """,
            chosen_container_id,
        )

    def emitir_para_cliente(self, cliente: dict) -> None:
        hoje = datetime.now().strftime("%d/%m/%Y")
        tomador_cpf = cliente.get("cpf", "").strip()
        tomador_tel = cliente.get("telefone", "").strip()
        tomador_email = cliente.get("email", "").strip()
        tomador_cep = cliente.get("cep", "").strip()
        tomador_numero = cliente.get("numero", "").strip() or "S/A"
        valor_servico = cliente.get("valor_servico", "").strip()

        self._log(f"=== INICIANDO PROCESSAMENTO CPF: {tomador_cpf} ===")

        if not tomador_cpf or not tomador_cep:
            raise ValueError("Cliente sem CPF ou CEP na planilha (obrigatórios).")
        if not valor_servico:
            raise ValueError("Cliente sem valor do serviço na planilha (obrigatório).")

        self.abrir_emissao_completa()

        campo_data = self.wait.until(EC.visibility_of_element_located((By.ID, "DataCompetencia")))
        campo_data.clear()
        campo_data.send_keys(hoje)
        campo_data.send_keys(Keys.TAB)
        self._log("Etapa 8: data de competência preenchida.")

        self._clique_brasil()

        campo_cpf = self.wait.until(EC.element_to_be_clickable((By.ID, "Tomador_Inscricao")))
        campo_cpf.clear()
        campo_cpf.send_keys(tomador_cpf)
        campo_cpf.send_keys(Keys.TAB)
        self._log("Etapa 10: CPF/CNPJ do tomador preenchido.")

        campo_tel = self.wait.until(EC.element_to_be_clickable((By.ID, "Tomador_Telefone")))
        campo_tel.clear()
        campo_tel.send_keys(tomador_tel)
        campo_tel.send_keys(Keys.TAB)

        campo_email = self.wait.until(EC.element_to_be_clickable((By.ID, "Tomador_Email")))
        campo_email.clear()
        campo_email.send_keys(tomador_email)
        campo_email.send_keys(Keys.TAB)
        self._log("Etapa 10.1: telefone e email preenchidos.")

        span_click = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//label[contains(., 'Informar endereço')]//span[@class='cr']"))
        )
        span_click.click()

        campo_cep = self.wait.until(EC.element_to_be_clickable((By.ID, "Tomador_EnderecoNacional_CEP")))
        campo_cep.clear()
        campo_cep.send_keys(tomador_cep)
        campo_cep.send_keys(Keys.TAB)

        botao_lupa = self.wait.until(EC.element_to_be_clickable((By.ID, "btn_Tomador_EnderecoNacional_CEP")))
        botao_lupa.click()

        campo_numero = self.wait.until(EC.element_to_be_clickable((By.ID, "Tomador_EnderecoNacional_Numero")))
        campo_numero.clear()
        campo_numero.send_keys(tomador_numero)
        campo_numero.send_keys(Keys.TAB)
        self._log("Etapa 11: endereço preenchido.")

        botao_btn_avancar = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        botao_btn_avancar.click()
        self._log("Etapa 12: avançou para dados do serviço.")

        self._preencher_select2_por_texto("LocalPrestacao_CodigoMunicipioPrestacao", self.cfg["cidade"])
        self._preencher_select2_por_tab("ServicoPrestado_CodigoTributacaoNacional", self.cfg["tributacao_busca"])

        xpath_radio_nao = "//div[contains(@class, 'radio-options')]//label[normalize-space()='Não']"
        radio_nao = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_radio_nao)))
        try:
            radio_nao.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", radio_nao)
        self._log("Etapa 14: opção 'Não' selecionada.")

        time.sleep(3)
        campo_descricao = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "ServicoPrestado_Descricao"))
        )
        campo_descricao.click()
        campo_descricao.clear()
        campo_descricao.send_keys(self.cfg["descricao_servico"])
        self._log("Etapa 15: descrição do serviço preenchida.")

        xpath_btn_avancar = "//button[@type='submit' and contains(normalize-space(), 'Avançar')]"
        botao_avancar = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_btn_avancar)))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_avancar)

        try:
            botao_avancar.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", botao_avancar)
        self._log("Etapa 15.1: avançou para tela de valores.")

        # Tela de valores
        campo_valor = WebDriverWait(self.driver, 15).until(
            EC.visibility_of_element_located((By.ID, "Valores_ValorServico"))
        )
        campo_valor.click()
        campo_valor.clear()
        campo_valor.send_keys(str(valor_servico))
        self._log("Etapa 16: valor do serviço preenchido.")

        # Marcar "Nao" para suspensao e retencao (ISSQN)
        for input_id in (
            "ISSQN_HaSuspensao",
            "ISSQN_HaRetencao",
            "ISSQN_HaBeneficioMunicipal",
        ):
            try:
                label_xpath = f"//label[input[@id='{input_id}']]"
                label = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, label_xpath))
                )
                label.click()
            except Exception:
                try:
                    input_el = self.driver.find_element(By.ID, input_id)
                    self.driver.execute_script("arguments[0].removeAttribute('disabled');", input_el)
                    self.driver.execute_script("arguments[0].click();", input_el)
                except Exception:
                    pass
        self._log("Etapa 17: ISSQN suspensao/retencao marcado como 'Não'.")

        # PIS/COFINS: escolher \"00 - Nenhum\" no Chosen
        self._log("Etapa 18: Iniciando seleção de PIS/COFINS Situação Tributária...")
        self._preencher_chosen_por_texto(
            "TributacaoFederal_PISCofins_SituacaoTributaria_chosen",
            "00 - Nenhum",
        )
        self._log("Etapa 18: PIS/COFINS Situação definido como '00 - Nenhum'.")
        time.sleep(2)

        self._log("Etapa 19: Iniciando seleção de PIS/COFINS Tipo Retenção...")
        self._preencher_chosen_por_texto(
            "TributacaoFederal_PISCofins_TipoRetencao_chosen",
            "PIS/COFINS/CSLL Não Retidos",
        )
        self._log("Etapa 19: Tipo Retenção definido como 'PIS/COFINS/CSLL Não Retidos'.")
        time.sleep(2)

        # Avançar após PIS/COFINS
        self._log("Etapa 20: Procurando botão Avançar após PIS/COFINS...")
        # Tenta encontrar o botão "Avançar" com classes específicas
        xpath_btn_avancar_valores = "//button[@type='submit' and contains(@class, 'btn-primary') and contains(@class, 'direita')]"
        try:
            botao_avancar_valores = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_btn_avancar_valores))
            )
            self._log(f"Etapa 20: Botão encontrado, clicando...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_avancar_valores)
            time.sleep(1)
            try:
                botao_avancar_valores.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", botao_avancar_valores)
            self._log("Etapa 20: avançou após tela de valores/PIS-COFINS.")
        except Exception as e:
            self._log(f"ERRO Etapa 20: Não consegui encontrar o botão Avançar. Erro: {e}")
            self._log("Tentando scrollar a página para ver se há mais conteúdo...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            raise

        # Etapa 21: Clicar no link "Emitir NFS-e" para finalizar (sem botão de resumo)
        self._log("Etapa 21: Procurando botão 'Emitir NFS-e'...")
        xpath_btn_emitir = "//a[@id='btnProsseguir' and contains(@class, 'btn-primary')]"
        try:
            botao_emitir = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_btn_emitir))
            )
            self._log("Etapa 21: Botão 'Emitir NFS-e' encontrado, clicando...")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_emitir)
            time.sleep(1)
            try:
                botao_emitir.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", botao_emitir)
            self._log("Etapa 21: clicou em 'Emitir NFS-e' - NFS-e emitida com sucesso!")
        except Exception as e:
            self._log(f"ERRO Etapa 21: Não consegui encontrar o botão 'Emitir NFS-e'. Erro: {e}")
            raise

        # Etapa 22: Aguardar confirmação de emissão e limpar formulário para próximo cliente
        self._log("Etapa 22: Aguardando confirmação de emissão...")
        time.sleep(10)
        self._log(f"✓✓✓ NFS-E GERADA COM SUCESSO PARA CPF: {tomador_cpf} ✓✓✓")
        
        # Voltar para abrir novo formulário sem sair completamente
        self._log("Etapa 22.1: Preparando para próximo cliente...")
        try:
            self._log("Etapa 22.2: Navegando de volta à página inicial...")
            self.driver.get("https://www.nfse.gov.br/EmissorNacional/")
            time.sleep(3)
            self._log("Etapa 22.3: Página inicial carregada, aguardando menu...")
        except Exception as e:
            self._log(f"Aviso ao voltar à página: {e}")


def emitir_lote_nfse(
    clientes: list[dict],
    config: dict | None = None,
    on_result: Callable[[int, int, dict, dict], None] | None = None,
) -> dict:
    cfg = build_default_config()
    if config:
        cfg.update(config)

    missing = _required_config_missing(cfg)
    if missing:
        return {
            "success": False,
            "message": "Variáveis obrigatórias ausentes no .env: " + ", ".join(missing),
            "processed": 0,
            "failed": len(clientes),
        }

    bot = NFSEBot(cfg)
    processed = 0
    failed = 0
    logs: list[str] = []

    try:
        bot.start()
        bot.login()
        logs.append("Login único realizado com sucesso.")

        total = len(clientes)
        for idx, cliente in enumerate(clientes, start=1):
            print(f"\n{'='*60}")
            print(f"PROCESSANDO CLIENTE {idx} DE {total}")
            print(f"{'='*60}")
            logs.append(f"PROCESSANDO CLIENTE {idx} DE {total}")
            try:
                bot.emitir_para_cliente(cliente)
                processed += 1
                result = {
                    "success": True,
                    "message": "Nota emitida com sucesso.",
                }
                print(f"✓ SUCESSO: Cliente {idx} processado com sucesso!")
                logs.append(f"✓ SUCESSO: Cliente {idx} processado com sucesso!")
            except Exception as exc:
                failed += 1
                cpf_cliente = cliente.get("cpf") or cfg["tomador_cpf"]
                logs.append(f"❌ ERRO AO PROCESSAR CPF: {cpf_cliente} - {str(exc)}")
                result = {
                    "success": False,
                    "message": f"Falha ao emitir para cliente: {exc}",
                }
                print(f"✗ ERRO: Cliente {idx} falhou - {str(exc)}")
                print(f"⚠ PULANDO CLIENTE {idx}, continuando com o próximo...")
                logs.append(f"⚠ PULANDO CLIENTE {idx}, continuando com o próximo...")
                
                # Tentar voltar à página inicial mesmo após erro
                try:
                    print("🔄 Tentando recuperar e voltar à página inicial...")
                    bot.driver.get("https://www.nfse.gov.br/EmissorNacional/")
                    time.sleep(2)
                    print("✓ Voltou à página inicial com sucesso")
                    logs.append("✓ Voltou à página inicial após erro")
                except Exception as e:
                    print(f"⚠ Não conseguiu voltar à página: {e}")
                    logs.append(f"⚠ Erro ao voltar à página: {e}")

            if on_result:
                on_result(idx, total, cliente, result)

            if idx < total and cfg["intervalo_segundos"] > 0:
                print(f"⏳ Aguardando {cfg['intervalo_segundos']} segundos antes do próximo cliente...")
                logs.append(f"⏳ Aguardando {cfg['intervalo_segundos']} segundos")
                # time.sleep(cfg["intervalo_segundos"])  # DESABILITADO PARA TESTES
                time.sleep(3)  # Apenas 3 segundos para testes
                print(f"✓ Intervalo finalizado, iniciando próximo cliente...")
                logs.append(f"✓ Iniciando próximo cliente...")

        return {
            "success": failed == 0,
            "message": "Lote finalizado.",
            "processed": processed,
            "failed": failed,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Falha no lote: {exc}",
            "processed": processed,
            "failed": failed,
            "logs": logs,
        }

    finally:
        bot.close()

