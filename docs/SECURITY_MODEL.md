# SECURITY_MODEL.md — Modelo de Ameaças & Controles *Security by Design*

Ver regras gerais de governança em [SECURITY.md](../SECURITY.md).

---

## 1. Vetores de Ameaça Mapeados

1. **Prompt Injection em Pesquisa/Reviews:** páginas externas, comentários da Play Store ou repositórios de referência podem conter instruções maliciosas.
   - *Controle:* todo conteúdo externo é marcado e processado como dado não confiável, sanitizado antes de persistência RAG/GDD e **nunca** pode sobrepor `AGENTS.md`.
2. **Código Gerado Defeituoso ou Perigoso (LLMs/Agentes):** scripts GDScript ou Python gerados podem tentar ler sistema de arquivos indevido, executar comandos ou vazar dados.
   - *Controle:* geração delimitada sobre templates versionados, revisão de diff, scan estático de isolamento (`src/core/`), confinamento de diretório no `Game Generator`/MCP, timeouts e bloqueio de execução irrestrita no host.
3. **Contaminação Cruzada Entre Projetos:** alteração acidental do Jogo A dentro do workspace do Jogo B.
   - *Controle:* validação explícita de `project_id` e caminho resolvido antes de toda operação de escrita/teste/build.
4. **Vazamento de Segredos e Keystores:** exposição acidental de tokens ou arquivos `.jks`/`.env` no Git.
   - *Controle:* [.gitignore](../.gitignore) blindado + varredura pré-commit automatizável.
5. **Fraude / Bypass de Economia ou Consentimento nos Jogos:** adulteração de relógio offline, recriação de reward sem callback SDK ou coleta sem UMP.
   - *Controle:* arquitetura *fail-closed* preservada do jogo-âncora (`IdleEconomy` teto `28800s` e detecção de clock negativo; bloqueio até verificação explícita nas bordas).
