# QA_STRATEGY.md — Estratégia de Qualidade & Quality Gates (Fábrica + Jogos)

Ver comandos concretos em [TESTING_STRATEGY.md](TESTING_STRATEGY.md).

---

## 1. Princípio Central

Qualidade **não** é um selo retórico: todo critério só é aprovado após execução real registrada com comando, commit, ambiente, contagem, exit code e data.

---

## 2. Os 4 Pilares de QA da PlayForge Factory (Alvo Fase 8)

1. **Validação Estática e Contratual (`Static + Schema Gates`):**
   - Checagem de schemas JSON (`GameSpecification`, configs de jogo), imports, referências `res://` quebradas, isolamento estrito (`core/` sem engine/SO/rede) e scan de segredos.
2. **Testes Determinísticos de Domínio (`Unit + Contract + Balance`):**
   - Regras puras em `< 1s`, PRNG seedável, relógio injetável e simuladores específicos por gênero (`BalanceVerifier`, `ActionBalanceVerifier`, extensíveis por plugin).
3. **Verificação de Engine & Gameplay (`Godot CLI Headless`):**
   - Boot de cenas sem `SCRIPT ERROR` nem nós vazados, smoke tests de entrada e fluxos críticos sem soft-lock.
4. **Auditoria de Assets, Desempenho & Build (`Pre-Release Audit`):**
   - Validação de licenças e proveniência de assets;
   - **Regra honesta de performance:** não declarar metas como `"Zero GC Alloc"` ou `"120 FPS"` como comprovadas sem medição/profiling real (FPS, frame time, memória, CPU) na plataforma-alvo. No estado atual do jogo-âncora (`Fase 0`), o código evita alocações óbvias nos loops via buffers pré-alocados, mas **ainda não passou por profiling real em aparelho Android**.

---

## 3. Quality Gates Obrigatórios para Considerar Uma Entrega Pronta

1. Especificação OpenSpec aprovada | 2. Implementação + tipagem/validação | 3. Análise estática sem infrações | 4. Testes aplicáveis aprovados pós-última edição | 5. Assets e licenças verificados (quando houver) | 6. Build validado (quando aplicável) | 7. Documentação, `SESSION_STATE.md` e OpenSpec atualizados.
