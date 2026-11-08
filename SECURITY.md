# Segurança

Relate vulnerabilidades pelo recurso **Private vulnerability reporting** do GitHub. Não abra issue pública com token, e-mail, protocolo, foto privada, regra de acesso ou instrução de exploração.

O mantenedor deve confirmar o recebimento, avaliar impacto, preparar correção e publicar orientação de atualização. Testes devem usar contas e dados isolados.

São suportados apenas o código do branch `main` e a release de modelo declarada em `config/settings.json`.


A CI executa Gitleaks 8.24.3 (binário com SHA-256 verificado) sobre o snapshot de
texto rastreado e um canário gerado; não publica valores/findings. Não audita o
histórico Git ou binários, e não substitui revisão humana. `pip-audit` consulta
vulnerabilidades conhecidas para os locks de runtime e ferramentas; indisponibilidade
da auditoria reprova o gate. Não há exceções de CVE configuradas.

Em incidente: revogue/rotacione o segredo no provedor antes de remover o texto;
não publique o valor, não reescreva o histórico sem coordenação do mantenedor e
não conclua que apagar um commit revoga a credencial. Artifacts de CI são uma
lista explícita de resumos técnicos, sem exports de usuários ou findings.
