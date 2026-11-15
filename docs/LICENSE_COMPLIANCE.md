# LICENSE_COMPLIANCE.md — Governança de Licenças & Proveniência

## 1. Regra de Conformidade

Nenhuma ferramenta, biblioteca, modelo de IA ou asset deve ser incorporado à fábrica ou a um jogo produzido sem verificação explícita da licença aplicável e registro de compatibilidade comercial.

---

## 2. Matriz Inicial de Tecnologias Previstas

| Componente | Licença Conhecida (a validar na adoção) | Condições / Cuidados Principais |
| :--- | :--- | :--- |
| **Godot Engine 4.x** | MIT | Uso comercial livre; incluir aviso MIT conforme exigência padrão em builds |
| **Python / FastAPI / LangGraph / PostgreSQL / pgvector** | MIT / PSF / PostgreSQL License | Permissivas para uso interno e comercial (verificar pacotes transitivos em cada fase) |
| **Valkey** | BSD 3-Clause *(verificar versão exata na imagem)* | Alternativa open-source gratuita a Redis |
| **n8n Community Edition** | **Sustainable Use License** | **Restrição importante:** permitido para automação interna do negócio; **proibido** expor editor a terceiros como SaaS/componente comercial sem licenciamento específico. Consultar versão vigente na Fase 9 antes de implantar |
| **Modelos Ollama** | Variável por modelo (Apache-2.0, MIT, Llama Community License, etc.) | Verificar a licença **individual** de cada modelo antes de usá-lo para gerar conteúdo/código de jogos comerciais |
| **Assets / Áudio / Fontes** | Original (`_draw()` / WAV procedural) ou CC0 / OFL / MIT verificadas | Proibido usar recursos sem fonte rastreável; conferir exigência de atribuição quando houver |
