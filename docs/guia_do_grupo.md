# Guia de testes do grupo

[Voltar ao projeto](../README.md)

## Começar

1. Abra https://ecoscan-gabrielhamad.streamlit.app/ no celular ou computador.
2. Como visitante, experimente Escanear, Descarte, Mapa e Aprender.
3. Para enviar correções vinculadas ao perfil, abra Entrar ou criar conta.
4. Informe seu próprio e-mail, crie uma senha e confirme o link recebido.
5. Volte ao aplicativo e entre. Não compartilhe senha com o grupo.

Se o cadastro não estiver disponível, peça ao mantenedor para conferir a
configuração. Se o e-mail não chegar, confira spam e use o reenvio disponível,
respeitando o intervalo. O projeto ainda precisa completar a recuperação de senha.

## Testar uma imagem

Use um objeto seguro e dentro do escopo: lata, PET, papelão, embalagem de vidro,
pilha doméstica ou um dos pequenos eletrônicos definidos no README. Fotografe
sem pessoas, documentos, localização visível ou dados de saúde.

Teste mudanças reais de iluminação, fundo e ângulo. Inclua objetos amassados ou
dobrados que já estejam seguros para manusear; não quebre vidro nem abra baterias.
Comece com um objeto por imagem. Vários objetos são um cenário difícil, não uma
capacidade garantida de detecção individual.

Confira o resultado, a orientação e, quando disponibilizadas, as etapas de
processamento. Não trate o valor de confiança como probabilidade garantida de acerto.
Se errar, envie a correção pelo app com consentimento, categoria esperada e estado
do objeto. Guarde o protocolo e acompanhe a resposta no Perfil.

## Roteiro de aceite

| Teste | Resultado esperado |
| --- | --- |
| Visitante analisa foto | Resultado temporário; sem pontos ou contribuição permanente |
| Conta não confirmada tenta entrar | Acesso autenticado recusado |
| Conta confirmada entra | Perfil reconhecido, sem acesso administrativo automático |
| Participante envia correção | Confirmação/protocolo ou erro claro; não sucesso fictício |
| Analista autorizado revisa | Encontra a contribuição e registra decisão/resposta |
| Autor retorna em outra sessão | Consulta seu protocolo com banco configurado |
| Outro participante consulta o Perfil | Não vê protocolos privados do primeiro |
| Imagem inválida ou fora do escopo | Tratamento de erro/incerteza, sem destino garantido |
| Abrir mapa e filtrar material | Lista parcial de São Paulo; aceitação específica não presumida |
| Consultar Aprender | Conteúdo e fonte correspondentes ao material |

O teste entre contas exige a colaboração do mantenedor: não forneça sua senha
para o analista e não tente acessar registros de outras pessoas por meios indevidos.
Cadastro confirmado não significa que uma contribuição foi enviada.

## Registro de uma rodada

Registre data, versão/commit se conhecido, dispositivo, navegador, cenário,
categoria esperada, resultado, método de captura e situação final. Para erros de
interface, inclua passos reproduzíveis e captura sem informações privadas.

Separe três tipos de problema: falha de interface, falha de persistência e erro
do reconhecimento. Anote também casos corretos para evitar medir apenas erros.
Não use as mesmas fotos para treinar e anunciar melhoria de acurácia.

## O que acontece com a contribuição

A secretaria aprova, rejeita ou corrige a anotação e responde ao protocolo.
Somente exemplos aprovados entram na preparação de um candidato. O candidato
precisa de avaliação independente e publicação pelo responsável; nenhuma foto
retreina automaticamente o aplicativo.

## Dificuldades comuns

- **Câmera indisponível:** use HTTPS, confira a permissão do navegador ou envie pela galeria.
- **Link local não abre no celular:** use o endereço público; localhost aponta para o próprio aparelho.
- **Mudança ainda não apareceu:** aguarde a implantação, recarregue e avise o mantenedor com horário e tela.
- **Falha ao enviar:** confira se o protocolo já existe antes de reenviar; pode ter ocorrido falha de confirmação.
- **Categoria incorreta:** não siga automaticamente a orientação; consulte Descarte e reporte para revisão.

Não há atendimento municipal real, comprovação de reciclagem ou garantia de
disponibilidade contínua neste piloto.
