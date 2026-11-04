# Escopo de residuos e variacoes

## Decisao de produto

Prioridade de engenharia, nao ranking estatistico de dano ambiental:

| Grupo | Objetos-alvo | Variacoes a coletar e avaliar |
| --- | --- | --- |
| Metal | Lata de bebida; lata de conserva vazia | Inteira, amassada, achatada, rotulo, sem rotulo, diferentes cores |
| Plastico | Garrafa PET; pote/frasco rigido vazio | Transparente, colorido, amassado, com/sem tampa e rotulo |
| Papel/papelao | Caixa; folha; jornal | Montado, desmontado, dobrado, rasgado, impresso |
| Vidro | Garrafa; pote de embalagem | Transparente, verde, marrom, inteiro; cacos como caso dificil separado |
| Pilhas | Pilhas domesticas AA/AAA; bateria portatil como caso sujeito a revisao | Diferentes marcas, tamanhos, unidades e grupos |
| Eletronicos | Celular, mouse, carregador de celular | Frente, verso, lateral, com/sem cabo, diferentes modelos |
| Orientacao assistida | Oleo de cozinha usado | Conteudo confirmado pelo usuario, nunca inferido da cor do liquido |
| Orientacao assistida | Medicamentos domiciliares de uso humano vencidos ou sem uso | Confirmacao do usuario; nao identificar comprimidos, conteudo ou validade pela foto |

Nao ampliar o treino para todos os aparelhos ou todos os plasticos. Os relatos
devem preferir os objetos especificos da tabela. O modelo retorna categorias de
material, nao certifica subtipo ou composicao. Novos nomes nao aumentam a precisao.

## Destinacao

- Embalagens: remover conteudo e consultar aceitacao da coleta local. Embalagem
  contaminada nao recebe destino apenas pela categoria visual. Papel molhado ou
  engordurado exige confirmacao, nao a mesma resposta de papelao seco.
- Vidro: cacos sao cortantes; nao manipular para obter fotos melhores. A aparencia
  nao distingue com seguranca embalagem, ceramica, espelho e vidro especial.
  Confirmar origem e orientacao de acondicionamento com a coleta local.
- Pilhas/eletronicos: ponto especifico de logistica reversa, nao coleta seletiva
  comum. Nao desmontar baterias. Apagar dados pessoais antes de entregar celulares.
- Oleo de cozinha: deixar esfriar, guardar em PET fechada, sem misturar produtos,
  consultar ponto que aceite oleo. Nao confundir recipiente cheio com PET vazia.
  Nao criar missao que confirme entrega, volume ou identidade do liquido pela foto.

Fontes oficiais:
- https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/medicamentos-seus-residuos-e-embalagens/
- https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/embalagens-em-geral/
- https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/eletroeletronicos/
- https://prefeitura.sp.gov.br/web/sesana/w/doe-seu-oleo-usado
- https://prefeitura.sp.gov.br/web/comunicacao/w/cuide_da_cidade/noticias/276265

## Validacao antes de liberar reconhecimento

1. Anotar objeto, estado, origem, consentimento/licenca e identidade da cena.
2. Separar treino/validacao/teste por objeto e sessao ANTES de gerar aumentos.
   Fotos vizinhas do mesmo video ou angulos do mesmo objeto nao podem cruzar conjuntos.
3. Coletar exemplos reais amassados/dobrados. Rotacao e filtros artificiais nao
   substituem deformacoes reais. Manter original e rastrear processamento aplicado.
4. Medir precisao, revocacao, confusoes e taxa de abstencao por categoria E estado.
   Comparar processamento automatico com imagem original no conjunto independente.
5. Testar desconhecidos: ceramica, alimentos, liquidos e objetos fora da lista.
   Evitar que a reducao de classes force qualquer foto para uma categoria aceita.
6. Avaliar video por cena/dispositivo, latencia e estabilidade; acerto em foto nao
   comprova rastreamento nem deteccao simultanea de objetos.

## Governanca do acervo

Antes de liberar espaco, guardar manifesto e backup dos originais, reservar
negativos independentes para teste de rejeicao e reconstruir os conjuntos a partir
das fontes auditadas. Remover uma imagem nao modifica um artefato ja publicado.
Toda nova release precisa registrar dados, contrato de preparacao, metricas e hash.
