# Documento de Design e Arquitetura: PC Performance Tray Hub

**Data:** 17 de Outubro de 2026  
**Status:** Revisado e Aprovado  
**Autor:** Antigravity AI & Breno  
**Localização:** `docs/specs/2026-10-13-pc-performance-tray-design.md`

---

## 1. Visão Geral e Intenção (The Why)

### 1.1 Contexto
O usuário necessita de uma central de otimização de desempenho, monitoramento térmico e controle de recursos para uso contínuo no Windows 10/11. O sistema deve operar silenciosamente em segundo plano, posicionado na bandeja do sistema (área de notificação da barra de tarefas, ao lado do relógio), com consumo de recursos praticamente nulo (< 25 MB de RAM e ~0% de CPU).

### 1.2 O Problema a Resolver
* Utilitários convencionais são pesados, instalam serviços desnecessários e consomem muita memória.
* A máquina possui sensibilidade térmica e elétrica (Core i7-7700, conector da placa-mãe suscetível a picos de corrente), necessitando de controle rápido entre perfis de energia (Turbo / Desempenho Máximo vs Equilibrado vs Silencioso) e alívio de processos pesados.
* O usuário quer poder alternar tudo com **1 clique** ou via **atalhos globais de teclado**, sem abrir janelas grandes ou interromper tarefas.

---

## 2. Decisões de Comportamento e Respostas do Revisor

Com base na rodada de alinhamento com o usuário e a auditoria de engenharia de sistemas Windows:

1. **Suspensão de Launchers (Decisão do Usuário - Opção B):**
   * Em vez de encerrar os programas, o aplicativo utiliza **Congelamento/Suspensão de Processos** (`NtSuspendProcess` / Windows EcoQoS) para os launchers detectados (Steam, Epic, Discord, Docker, etc.).
   * Isso zera o uso de CPU instantaneamente sem fechar os programas, permitindo retomá-los com um segundo clique sem precisar reabrir ou logar novamente.
2. **Controle Real de Ventoinha / Fan Speed (Decisão do Usuário - Opção A):**
   * O aplicativo incorpora a biblioteca de baixo nível `LibreHardwareMonitorLib` para se comunicar diretamente com o chip Super I/O da placa-mãe.
   * Permite leitura da temperatura real da junção da CPU (`IA32_THERM_STATUS`) e controle direto da rotação (RPM) da ventoinha do cooler (forçando 100% no modo Turbo).
3. **Modelo de Execução e Inicialização Silenciosa (Decisão Técnica da Engenharia):**
   * Binário único e ultra-leve.
   * Para executar tarefas com privilégio administrativo (limpeza de Standby List, controle de hardware) sem exibir tela chata de UAC a cada boot, o aplicativo se registra no **Agendador de Tarefas do Windows (`schtasks`)** com inicialização em logon e privilégios elevados (`HighestAvailable`).
4. **Otimização de Rede Não-Destrutiva (Decisão Técnica da Engenharia):**
   * Otimizador de latência focado em ações transitórias e seguras: esvaziamento de cache DNS (`DnsFlushResolverCache` / `ipconfig /flushdns`) e limpeza de tabelas ARP, **sem resetar sockets TCP bruscamente** e **sem exigir reinicialização do sistema**.

---

## 3. Metas, Não-Metas e Anti-Metas

### 3.1 Metas (Goals)
1. **Executável Ultra-Leve:**
   * Pegada de memória em repouso inferior a **25 MB de RAM**.
   * Uso de CPU em repouso de **~0.0%**.
   * Inicialização instantânea (< 500 ms) ao clicar no ícone.
2. **Presença na Bandeja do Sistema (System Tray):**
   * Ícone persistente ao lado do relógio do Windows.
   * Texto dinâmico no ícone mostrando a temperatura da CPU ou status ativo.
   * Clique esquerdo abre o **Flyout Flutuante Moderno (Fluent Acrylic)** ancorado no canto inferior direito.
   * Clique direito abre menu de contexto super-rápido para alternar perfis sem abrir janela.
3. **Arsenal de Otimizações:**
   * **Seletor de Perfis Rápidos:** Alternância instantânea de esquemas de energia do Windows (`powercfg` / Win32 Power APIs): Turbo (Desempenho Máximo), Equilibrado e Eco/Frio.
   * **Limpador de Memória RAM:** Esvaziamento instantâneo da *Standby List* e *Working Set* de processos em segundo plano via chamadas nativas de kernel (`EmptyWorkingSet`), recuperando gigabytes de RAM sem travar softwares.
   * **Congelador de Launchers:** Suspensão e retomada de processos gastões em segundo plano (Steam, Epic Games Launcher, EA Desktop, Discord, Docker Desktop, Overwolf).
   * **Controle Real de Ventoinha:** Slider de 30% a 100% de velocidade do cooler e modo forçar 100% para jogos.
   * **Check-up Rápido de Saúde (Item 3):** Análise instantânea de saúde dos discos (SMART via WMI de SSDs/HDDs), checagem de erros críticos de Kernel recentes e pontuação de integridade geral.
   * **Atalhos Globais de Teclado (Item 4):** Hotkeys configuráveis (ex: `Ctrl + Shift + F12` para limpar RAM; `Ctrl + Shift + F11` para alternar para Turbo) registradas via `RegisterHotKey` na API do Windows.
   * **Otimizador de Rede e Latência (Item 5):** Esvaziamento de cache DNS (`DnsFlushResolverCache`) e otimização de pilha sem necessidade de reinício.
4. **Interface Fluent Moderna & Gadgets Personalizáveis:**
   * Estilo visual inspirado na **Opção B (Fluent Clean / Acrylic Dark)**.
   * Cada gadget no painel pode ser ativado, desativado ou reordenado pelo usuário.

### 3.2 Não-Metas (Non-Goals)
* O software **não** é um antivírus nem uma ferramenta invasiva de registro.
* O software **não** aplica overvoltage agressivo que possa danificar circuitos.

### 3.3 Anti-Metas (Anti-Goals)
* **Nunca travar a interface:** Nenhuma operação de otimização roda na thread da interface. Tudo é assíncrono.
* **Nunca fechar documentos não salvos:** O congelador de processos suspende apenas launchers e ferramentas auxiliares, preservando 100% o estado da sessão.

---

## 4. Identidade Visual, Teoria das Cores & Full Night Mode (Aprovado)

* **Eliminação Total de Emojis:** Nenhum emoji de sistema é utilizado na interface. Todos os glifos são ícones vetoriais lineares (SVG) monocromáticos com traço fino (1.5px/2px), alinhados com a tipografia nativa do Windows.
* **Paleta Estrita de Teoria das Cores (True Night Mode):**
  * `Void Black` (`#04060A`): Fundo base absoluto sem emissão de luz parasita.
  * `Obsidian Surface` (`#080C14` / `#0D111A`): Superfície dos cartões de gadget com bordas milimétricas em `#161E2E`.
  * `Azure Precision` (`#38BDF8` sobre `#1E3A8A`): Acento único de harmonia cromática reservado para o estado ativo e ações de turbo.
  * `Emerald Semantic` (`#10B981`): Acento semântico exclusivo para confirmação de temperatura segura e saúde SMART de discos.
* **Ergonomia e Tipografia:** Segoe UI Variable Text com fontes monoespaçadas (`Consolas` / `tabular-nums`) para frequências de GHz, RPM da ventoinha e temperatura da CPU, garantindo estabilidade e repouso ocular.
* **Feedback Físico:** Animações sutis com `scale(0.98)` nos cliques, transição de barras com cubic-bezier suave e slide-up de 12px ao abrir o flyout.

---

## 5. Arquitetura dos Gadgets Modulares (Sem Emojis)

Cartões modulares independentes:
1. **Widget de Perfil Energético (Power Switcher):** Segmented control moderno (`Turbo Max`, `Equilibrado`, `Silencioso`) com badge de estado ativo.
2. **Widget de Telemetria de CPU & Temperatura:** Mostrador de Clock (GHz), % e Temperatura real do diodo da CPU via diodo térmico, com micro-barra de estado dinâmico.
3. **Widget de Controle de Ventoinha / Cooler:** Slider e trava rápida em 100% de velocidade do fan via Super I/O com leitura em RPM.
4. **Widget de Limpeza de Memória RAM:** Medidor de RAM e botão com ícone SVG de vassoura linear: *"Limpar RAM (Standby List)"* com feedback imediato de MB liberados.
5. **Widget de Congelamento de Launchers:** Detecção de launchers e botão com ícone SVG de pausa linear: *"Pausar Launchers (0% CPU)"*.
6. **Widget de Check-up de Saúde do PC:** Indicador com ícone de escudo SVG para integridade de discos (SSD Walram + HD WD) e pontuação de integridade do sistema.
7. **Widget de Latência e Rede:** Botão com ícone de ondas de sinal SVG: *"Flush DNS & Latência"*.
8. **Configuração de Atalhos Globais:** Painel de configuração de teclas de atalho personalizáveis (`Ctrl+Shift+F12`, etc.).

---

## 6. Critérios de Sucesso e Validação

1. O executável inicia minimizado diretamente na bandeja sem piscar nenhuma janela na tela.
2. O consumo de memória RAM do processo em idle é menor que 25 MB.
3. Ao clicar no ícone da bandeja, o flyout abre instantaneamente no canto inferior direito.
4. Clicar em "Turbo Max" ativa o plano "Desempenho Máximo" do Windows em menos de 100 ms.
5. Clicar em "Limpar RAM" reduz o consumo de memória imediatamente.
6. A ventoinha responde aos comandos de velocidade através do LibreHardwareMonitorLib.
7. As hotkeys globais respondem mesmo enquanto um jogo está rodando em tela cheia.
