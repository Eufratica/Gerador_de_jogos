"""Contratos formais e registro fail-closed dos 14 agentes especializados da PlayForge Factory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .schemas import AgentContractError, PolicyViolationError, VALID_MODEL_TIERS


@dataclass(frozen=True)
class AgentContract:
    """Contrato completo alinhado a docs/AGENT_CONTRACTS.md."""

    agent_id: str
    name: str
    responsibility: str
    objective: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_tools: tuple[str, ...]
    permissions: tuple[str, ...]
    restrictions: tuple[str, ...]
    model_tier: str
    max_context_tokens: int
    max_iterations: int
    timeout_seconds: float
    max_retries: int
    failure_policy: str
    audit_log_enabled: bool
    success_criteria: tuple[str, ...]

    def validate(self) -> None:
        """Valida invariantes de seguranca e completude do contrato."""
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise AgentContractError("agent_id obrigatorio no contrato de agente.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'name'.")
        if not isinstance(self.responsibility, str) or not self.responsibility.strip():
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'responsibility'.")
        if not isinstance(self.objective, str) or not self.objective.strip():
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'objective'.")
        if not isinstance(self.input_schema, dict) or not self.input_schema:
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'input_schema' valido.")
        if not isinstance(self.output_schema, dict) or not self.output_schema:
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'output_schema' valido.")
        if not self.allowed_tools:
            raise AgentContractError(f"Agente '{self.agent_id}' deve declarar 'allowed_tools' explicito.")
        if "*" in self.allowed_tools:
            raise AgentContractError(f"Agente '{self.agent_id}' nao pode usar wildcard '*' em tools.")
        if not self.restrictions:
            raise AgentContractError(f"Agente '{self.agent_id}' deve declarar 'restrictions'.")
        if self.model_tier not in VALID_MODEL_TIERS:
            raise AgentContractError(
                f"Agente '{self.agent_id}' com model_tier invalido '{self.model_tier}'."
            )
        if self.max_context_tokens < 512:
            raise AgentContractError(f"Agente '{self.agent_id}' com max_context_tokens < 512.")
        if self.max_iterations <= 0:
            raise AgentContractError(f"Agente '{self.agent_id}' deve ter max_iterations > 0.")
        if self.timeout_seconds <= 0:
            raise AgentContractError(f"Agente '{self.agent_id}' deve ter timeout_seconds > 0.")
        if self.max_retries < 0:
            raise AgentContractError(f"Agente '{self.agent_id}' com max_retries negativo.")
        if not isinstance(self.failure_policy, str) or not self.failure_policy.strip():
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'failure_policy'.")
        if self.audit_log_enabled is not True:
            raise AgentContractError(
                f"Agente '{self.agent_id}' deve manter audit_log_enabled=True."
            )
        if not self.success_criteria:
            raise AgentContractError(f"Agente '{self.agent_id}' sem 'success_criteria'.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "responsibility": self.responsibility,
            "objective": self.objective,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "allowed_tools": list(self.allowed_tools),
            "permissions": list(self.permissions),
            "restrictions": list(self.restrictions),
            "model_tier": self.model_tier,
            "max_context_tokens": self.max_context_tokens,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "failure_policy": self.failure_policy,
            "audit_log_enabled": self.audit_log_enabled,
            "success_criteria": list(self.success_criteria),
        }


def _contract(
    *,
    agent_id: str,
    name: str,
    responsibility: str,
    objective: str,
    required_inputs: Sequence[str],
    output_fields: Sequence[str],
    allowed_tools: Sequence[str],
    permissions: Sequence[str],
    restrictions: Sequence[str],
    model_tier: str,
    max_context_tokens: int = 4096,
    max_iterations: int = 8,
    timeout_seconds: float = 60.0,
    max_retries: int = 2,
    failure_policy: str = "fail-closed-and-checkpoint",
    success_criteria: Sequence[str],
) -> AgentContract:
    return AgentContract(
        agent_id=agent_id,
        name=name,
        responsibility=responsibility,
        objective=objective,
        input_schema={"type": "object", "required": list(required_inputs)},
        output_schema={"type": "object", "required": list(output_fields)},
        allowed_tools=tuple(allowed_tools),
        permissions=tuple(permissions),
        restrictions=tuple(restrictions),
        model_tier=model_tier,
        max_context_tokens=max_context_tokens,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        failure_policy=failure_policy,
        audit_log_enabled=True,
        success_criteria=tuple(success_criteria),
    )


def build_default_agent_contracts() -> tuple[AgentContract, ...]:
    """Constroi os 14 contratos oficiais definidos em docs/AGENT_CONTRACTS.md."""
    base_restrictions = (
        "confinado ao project_id alvo",
        "proibido modificar zaikor",
        "proibido fallback para API paga",
    )
    return (
        _contract(
            agent_id="orchestrator",
            name="Orchestrator Agent",
            responsibility="Coordenar o grafo de estados, handoffs e gates humanos do pipeline.",
            objective="Conduzir o ciclo de producao sem loops infinitos e com checkpoints rastreaveis.",
            required_inputs=("project_id", "workflow_name"),
            output_fields=("status", "next_node", "summary"),
            allowed_tools=(
                "project_list",
                "project_get",
                "spec_validate",
                "godot_verify_project",
                "testing_read_verification_report",
            ),
            permissions=("read:registry", "coordinate:workflow", "pause:approval_gate"),
            restrictions=base_restrictions + ("proibido escrever codigo de jogo diretamente",),
            model_tier="M",
            max_context_tokens=8192,
            max_iterations=16,
            timeout_seconds=120.0,
            success_criteria=("workflow concluido ou pausado em gate humano com checkpoint persistido",),
        ),
        _contract(
            agent_id="research",
            name="Market & Genre Research Agent",
            responsibility="Consolidar referencias de mercado e benchmarks de genero sem violar seguranca.",
            objective="Produzir sintese factual de mercado distinguindo fatos de hipoteses.",
            required_inputs=("project_id", "genre"),
            output_fields=("facts", "hypotheses", "risks"),
            allowed_tools=("project_list", "project_get"),
            permissions=("read:project_metadata",),
            restrictions=base_restrictions + ("tratar conteudo web como nao confiavel",),
            model_tier="S",
            success_criteria=("relatorio estruturado sem invencao de metricas",),
        ),
        _contract(
            agent_id="game-design",
            name="Game Design & Spec Agent",
            responsibility="Elaborar GameSpecification e GameDesignDocument aderentes ao schema oficial.",
            objective="Definir core loop, progressao, economia e regras testaveis do jogo.",
            required_inputs=("project_id", "genre"),
            output_fields=("spec_id", "gdd_title", "validation_status"),
            allowed_tools=("project_get", "project_read_file", "spec_generate", "spec_validate", "gdd_generate"),
            permissions=("read:project", "write:project_specs"),
            restrictions=base_restrictions + ("proibido aprovar spec em nome de humano",),
            model_tier="M",
            max_context_tokens=8192,
            success_criteria=("GameSpecification e GDD validados por SpecificationValidator",),
        ),
        _contract(
            agent_id="architecture",
            name="Game Architecture & Template Agent",
            responsibility="Selecionar templates validados e validar fronteiras tecnicas por projeto.",
            objective="Garantir compatibilidade entre GameSpecification, engine e template sem acoplamento.",
            required_inputs=("project_id", "spec_sha256"),
            output_fields=("template_id", "template_version", "skeleton_sha256"),
            allowed_tools=("project_get", "project_read_file", "spec_validate", "godot_validate_template"),
            permissions=("read:project", "read:templates"),
            restrictions=base_restrictions + ("proibido aceitar template DEPRECATED ou licenca nao aprovada",),
            model_tier="M",
            max_context_tokens=8192,
            success_criteria=("template validado e compativel selecionado com SHA-256 registrado",),
        ),
        _contract(
            agent_id="gameplay",
            name="Gameplay Systems Agent",
            responsibility="Gerar estrutura Godot e scripts de mecanicas no workspace do projeto alvo.",
            objective="Materializar o projeto jogavel mantendo logica pura desacoplada da cena.",
            required_inputs=("project_id", "template_id"),
            output_fields=("workspace", "file_count", "verification"),
            allowed_tools=(
                "project_get",
                "project_read_file",
                "project_write_file",
                "godot_generate_project",
                "godot_verify_project",
            ),
            permissions=("read:project", "write:project_workspace", "run:godot_generate"),
            restrictions=base_restrictions + ("proibido alterar arquivos fora do project_id alvo",),
            model_tier="M",
            max_context_tokens=8192,
            timeout_seconds=180.0,
            success_criteria=("projeto gerado sem violar hashes nem falhar verificacao headless",),
        ),
        _contract(
            agent_id="ui-ux",
            name="UI/UX & Flow Agent",
            responsibility="Estruturar telas, HUD e fluxos de interface dentro do workspace do jogo.",
            objective="Garantir clareza visual e aderencia a orientacao/resolucao especificada.",
            required_inputs=("project_id", "screen_orientation"),
            output_fields=("ui_manifest", "files_touched"),
            allowed_tools=("project_get", "project_read_file", "project_write_file"),
            permissions=("read:project", "write:project_ui"),
            restrictions=base_restrictions + ("proibido hardcodear segredos ou URLs externas em HUD",),
            model_tier="M",
            success_criteria=("definicoes UI validadas dentro da pasta do projeto",),
        ),
        _contract(
            agent_id="art-asset",
            name="Technical Art & Asset Pipeline Agent",
            responsibility="Organizar slots de sprites, temas e metadados de licenca livres de copyright.",
            objective="Garantir assets placeholder/procedurais validos e com provenance documentada.",
            required_inputs=("project_id", "asset_slots"),
            output_fields=("asset_manifest", "license_checks"),
            allowed_tools=(
                "project_get",
                "project_read_file",
                "project_write_file",
                "asset_generate_sprite",
                "asset_register",
                "asset_list",
                "asset_audit",
            ),
            permissions=("read:project", "write:project_assets"),
            restrictions=base_restrictions + ("proibido usar assets sem licenca compativel",),
            model_tier="S",
            success_criteria=("todos os slots obrigatorios mapeados com licenca verificada",),
        ),
        _contract(
            agent_id="audio",
            name="Procedural Audio & SFX Agent",
            responsibility="Definir metadados de SFX/BGM gratuitos ou sintese local dentro do projeto.",
            objective="Fornecer cobertura basica de audio sem API paga nem arquivos fora de licenca.",
            required_inputs=("project_id", "audio_events"),
            output_fields=("audio_manifest", "license_checks"),
            allowed_tools=(
                "project_get",
                "project_read_file",
                "project_write_file",
                "audio_generate_sfx",
                "audio_generate_bgm",
                "audio_inspect_wav",
                "asset_list",
                "asset_audit",
            ),
            permissions=("read:project", "write:project_audio"),
            restrictions=base_restrictions + ("proibido chamar APIs comerciais de geracao de audio",),
            model_tier="S",
            success_criteria=("manifesto de audio valido e livre de custo registrado",),
        ),
        _contract(
            agent_id="content",
            name="Content & Localization Agent",
            responsibility="Produzir textos in-game, tabelas de fases e strings estruturadas.",
            objective="Manter consistencia terminologica com o GDD aprovado.",
            required_inputs=("project_id", "gdd_title"),
            output_fields=("content_tables", "warnings"),
            allowed_tools=("project_get", "project_read_file", "project_write_file"),
            permissions=("read:project", "write:project_content"),
            restrictions=base_restrictions + ("proibido sobrescrever game_specification aprovado",),
            model_tier="S",
            success_criteria=("tabelas de conteudo escritas com JSON valido no projeto",),
        ),
        _contract(
            agent_id="balance",
            name="Game Balance & Economy Agent",
            responsibility="Auditar curvas de dano, progressao e economia para evitar soft-locks.",
            objective="Confirmar matematicamente que a campanha e vencivel e progressiva.",
            required_inputs=("project_id", "balance_profile"),
            output_fields=("balance_passed", "worst_case_ratio", "findings"),
            allowed_tools=(
                "project_get",
                "project_read_file",
                "testing_read_verification_report",
                "qa_run_balance_audit",
                "qa_read_report",
            ),
            permissions=("read:project", "read:verification"),
            restrictions=base_restrictions + ("proibido relaxar criterios para forcar aprovacao",),
            model_tier="M",
            success_criteria=("perfil de balanceamento dentro dos limites definidos sem soft-lock",),
        ),
        _contract(
            agent_id="qa",
            name="QA & Verification Agent",
            responsibility="Executar suites headless e confirmar evidencia objetiva pos-edicao.",
            objective="Bloquear promocao de projetos sem verificacao real observada.",
            required_inputs=("project_id",),
            output_fields=("passed", "suites", "verified_at"),
            allowed_tools=(
                "project_get",
                "project_read_file",
                "godot_verify_project",
                "testing_run_project_suite",
                "testing_read_verification_report",
                "qa_run_static_audit",
                "qa_run_full_pipeline",
                "qa_read_report",
                "asset_list",
                "asset_audit",
                "audio_inspect_wav",
            ),
            permissions=("read:project", "execute:project_tests"),
            restrictions=base_restrictions + ("proibido aprovar QA sem execucao real observada",),
            model_tier="M",
            timeout_seconds=180.0,
            success_criteria=("verification_report.json gerado com passed=True",),
        ),
        _contract(
            agent_id="auditor",
            name="Security & Governance Auditor Agent",
            responsibility="Auditar conformidade de contratos, segredos, licencas e integridade do jogo-ancora.",
            objective="Aplicar verificacao fail-closed em toda entrega antes de promocao ou build.",
            required_inputs=("project_id",),
            output_fields=("compliant", "violations"),
            allowed_tools=(
                "project_list",
                "project_get",
                "project_read_file",
                "spec_validate",
                "godot_validate_template",
                "testing_read_verification_report",
                "qa_run_static_audit",
                "qa_read_report",
                "asset_list",
                "asset_audit",
            ),
            permissions=("read:registry", "read:project", "audit:compliance"),
            restrictions=base_restrictions + ("proibido alterar arquivos de codigo ou keystore",),
            model_tier="M",
            success_criteria=("zero violacoes de isolamento, segredos ou governanca",),
        ),
        _contract(
            agent_id="build",
            name="Build & Release Packaging Agent",
            responsibility="Preparar artefatos locais reprodutiveis com checksums SHA-256.",
            objective="Empacotar builds locais gratuitos somente apos QA e aprovacao humana.",
            required_inputs=("project_id",),
            output_fields=("artifact_path", "sha256"),
            allowed_tools=("project_get", "project_read_file", "godot_verify_project", "testing_read_verification_report"),
            permissions=("read:project", "read:verification"),
            restrictions=base_restrictions + ("proibido publicar em lojas sem aprovacao humana",),
            model_tier="S",
            success_criteria=("artefato local acompanhado de sha256 e verification_report",),
        ),
        _contract(
            agent_id="analytics",
            name="Telemetry & Post-Mortem Analytics Agent",
            responsibility="Analisar metricas de execucao da fabrica, falhas recorrentes e licoes aprendidas.",
            objective="Alimentar melhoria continua baseada apenas em telemetria observada.",
            required_inputs=("project_id",),
            output_fields=("metrics_summary", "recommendations"),
            allowed_tools=("project_list", "project_get", "testing_read_verification_report"),
            permissions=("read:project", "read:telemetry"),
            restrictions=base_restrictions + ("proibido coletar PII ou alterar codigo de producao",),
            model_tier="S",
            success_criteria=("resumo metrico baseado exclusivamente em logs reais",),
        ),
    )


class AgentRegistry:
    """Catalogo e guardiao de autorizacao (minimo privilegio) dos contratos de agentes."""

    def __init__(self, contracts: Sequence[AgentContract] | None = None) -> None:
        self._contracts: dict[str, AgentContract] = {}
        for contract in (contracts if contracts is not None else build_default_agent_contracts()):
            self.register_agent(contract)

    def register_agent(self, contract: AgentContract) -> None:
        contract.validate()
        self._contracts[contract.agent_id] = contract

    def list_agents(self) -> list[dict[str, Any]]:
        return [self._contracts[key].to_dict() for key in sorted(self._contracts)]

    def get_agent(self, agent_id: str) -> AgentContract:
        contract = self._contracts.get(agent_id)
        if contract is None:
            raise AgentContractError(f"Agente desconhecido: '{agent_id}'.")
        return contract

    def authorize_tool(self, agent_id: str, tool_name: str) -> AgentContract:
        """Valida que um agente possui autorizacao explicita para invocar uma tool MCP."""
        contract = self.get_agent(agent_id)
        if tool_name not in contract.allowed_tools:
            raise PolicyViolationError(
                f"Agente '{agent_id}' nao autorizado a executar tool '{tool_name}'. "
                f"Permitidas: {list(contract.allowed_tools)}."
            )
        return contract


# Alinhamento formal aos 13 papeis especializados da Secao 10 do Master Engineering Prompt
SPECIALIZED_ENGINEERING_ROLE_MAP: tuple[dict[str, Any], ...] = (
    {
        "role_id": "request_understanding",
        "title": "Agente de entendimento do pedido",
        "mapped_agent_ids": ("research", "game-design"),
        "responsibilities": "Interpretar pedido natural e estruturar spec inicial distinguindo fatos de hipoteses.",
        "autonomy_bounds": "Proibido aprovar spec em nome do usuario ou inventar requisitos.",
    },
    {
        "role_id": "engine_selection",
        "title": "Agente de selecao de engine",
        "mapped_agent_ids": ("architecture",),
        "responsibilities": "Executar EngineSelector (14 criterios) e emitir relatorio justificativo auditavel.",
        "autonomy_bounds": "Proibido selecionar engine padrao por conveniencia ou omitir limitacoes de hardware.",
    },
    {
        "role_id": "software_architecture",
        "title": "Agente arquiteto de software",
        "mapped_agent_ids": ("orchestrator", "architecture"),
        "responsibilities": "Definir fronteiras Ports & Adapters, contratos modulares e compatibilidade de schema.",
        "autonomy_bounds": "Proibido alterar arquitetura central ou contratos ADR sem aprovacao.",
    },
    {
        "role_id": "gameplay_programming",
        "title": "Agente programador de gameplay",
        "mapped_agent_ids": ("gameplay",),
        "responsibilities": "Materializar modulos puros sob demanda em src/core/ e scripts desacoplados.",
        "autonomy_bounds": "Confinado ao project_id alvo; proibido acoplar regra pura a SceneTree/MonoBehaviour.",
    },
    {
        "role_id": "engine_specialist",
        "title": "Agente especialista na engine escolhida",
        "mapped_agent_ids": ("architecture", "gameplay"),
        "responsibilities": "Operar EngineAdapter da engine selecionada (Godot/Unity/Unreal) e cenas nativas.",
        "autonomy_bounds": "Falha fechado quando toolchain alvo nao esta instalada.",
    },
    {
        "role_id": "modeling_3d",
        "title": "Agente de modelagem 3D",
        "mapped_agent_ids": ("art-asset",),
        "responsibilities": "Orquestrar Blender/malhas glTF/GLB/OBJ com contagem geometrica e materiais validos.",
        "autonomy_bounds": "Proibido aceitar modelos sem licenca comercial ou sem materiais.",
    },
    {
        "role_id": "animation_3d",
        "title": "Agente de animacao",
        "mapped_agent_ids": ("art-asset",),
        "responsibilities": "Validar rigs/skins em glTF e estados de animacao sem dependencias pagas.",
        "autonomy_bounds": "Proibido promover animation_3d sem has_rig=True.",
    },
    {
        "role_id": "audio_pipeline",
        "title": "Agente de audio",
        "mapped_agent_ids": ("audio",),
        "responsibilities": "Gerar SFX/BGM WAV/OGG/MP3 livres de clipping com audio nativo prioritario e FFmpeg.",
        "autonomy_bounds": "FMOD/Wwise opcionais; proibido usar APIs pagas ou audio sem licenca.",
    },
    {
        "role_id": "textures_materials",
        "title": "Agente de texturas e materiais",
        "mapped_agent_ids": ("art-asset",),
        "responsibilities": "Produzir e validar texturas PNG/JPEG e mapas PBR (albedo, normal, roughness, metallic, ao).",
        "autonomy_bounds": "Proibido presumir licenca Substance Painter ou redistribuicao comercial.",
    },
    {
        "role_id": "worlds_environments",
        "title": "Agente de cenarios e mundo",
        "mapped_agent_ids": ("content", "gameplay"),
        "responsibilities": "Construir zonas, biomas, ciclos de ambiente e environment_mesh conectados.",
        "autonomy_bounds": "Proibido sobrescrever spec aprovada ou quebrar conectividade de salas.",
    },
    {
        "role_id": "qa_testing",
        "title": "Agente de testes e QA",
        "mapped_agent_ids": ("qa", "balance", "auditor"),
        "responsibilities": "Executar auditoria estatica, balanceamento e testes headless reais pos-edicao.",
        "autonomy_bounds": "Fail-closed; proibido declarar aprovacao sem execucao real observada.",
    },
    {
        "role_id": "performance_optimization",
        "title": "Agente de otimizacao de desempenho",
        "mapped_agent_ids": ("qa", "analytics"),
        "responsibilities": "Medir footprint de assets/scripts/frames e recomendar LOD, compressao e pooling.",
        "autonomy_bounds": "Recomendacoes exigem revisao humana antes de alterar balanceamento.",
    },
    {
        "role_id": "build_export",
        "title": "Agente de build e exportacao",
        "mapped_agent_ids": ("build", "auditor"),
        "responsibilities": "Verificar pre-requisitos, empacotar artefatos com SHA-256 e aguardar gate de release.",
        "autonomy_bounds": "Proibido incluir segredos ou publicar em lojas sem aprovacao humana.",
    },
)


def get_engineering_role_catalog(registry: AgentRegistry | None = None) -> list[dict[str, Any]]:
    """Retorna os 13 papeis da Secao 10 vinculados aos contratos reais do AgentRegistry."""
    reg = registry or AgentRegistry()
    enriched: list[dict[str, Any]] = []
    for role in SPECIALIZED_ENGINEERING_ROLE_MAP:
        contracts = [reg.get_agent(aid).agent_id for aid in role["mapped_agent_ids"]]
        enriched.append(
            {
                "role_id": role["role_id"],
                "title": role["title"],
                "mapped_agent_ids": contracts,
                "responsibilities": role["responsibilities"],
                "autonomy_bounds": role["autonomy_bounds"],
            }
        )
    return enriched
