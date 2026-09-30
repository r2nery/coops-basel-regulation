# Cooperativas de crédito e bancos sob a mesma régua prudencial

> O que os dados do Banco Central mostram sobre o perfil das cooperativas que operam na metodologia completa de Basileia, 2017 a 2024
> Whitepaper. Sistema OCB, setembro de 2026.
> Arthur Gomes Nery, Thiago de Oliveira Victorino e Rodrigo Lima Rangel

<!-- Fonte do whitepaper em português. make_docx.py whitepaper gera o .docx no modelo de
     Briefing do Sistema OCB. Marcações: # título, > subtítulo, ## seção, ### subseção,
     - lista, 1. lista numerada, {{fig:...}}, {{table:t2|...}}, {{refs:...}}, {{pagebreak}}.
     Todos os números vêm do artigo e das tabelas geradas pelo pipeline. -->

## Sumário executivo

- Desde 2017, a cooperativa de crédito que cresce além de 0,1% do PIB em exposição, ou que abre mão do regime simplificado, calcula capital, risco e provisão pelas mesmas regras que um banco comercial.
- Este estudo compara 130 cooperativas singulares e 144 bancos nessa condição, com dados públicos do IF.data, de 2017 a 2024, em porte comparável.
- A cooperativa destina parcela maior do ativo ao crédito, tem retorno sobre ativos mais alto, custo menor e retorno menos volátil que o banco de porte semelhante.
- A diferença de capital é moderada em nível e grande em dispersão: as cooperativas ocupam uma faixa estreita do índice de Basileia, sem a cauda de bancos pequenos com índices acima de 50%.
- Duas diferenças citadas com frequência, provisão menor e margem mais estreita, desaparecem quando a comparação se restringe a bancos.
- Para a regulação proporcional, os resultados abrem dois eixos além do porte: o tratamento das redes cooperativas e a calibragem do benchmark. Alívio regulatório não decorre automaticamente desses achados.

## 1. Contexto

### 1.1 Uma régua comum

A regulação prudencial convergiu para um modelo único. Basileia III fornece a arquitetura de capital, alavancagem e mensuração de risco, e cada supervisor a adapta às condições locais. No Brasil, a Resolução CMN 4.553/2017 distribui as instituições autorizadas em cinco segmentos, segundo o porte e a atividade internacional. Os segmentos S1 a S4 aplicam a metodologia completa. O S5 reúne instituições com exposição inferior a 0,1% do PIB que optam pela metodologia simplificada de apuração do capital mínimo (Resolução 4.606/2017). Bancos comerciais, múltiplos, de investimento e de câmbio ficam fora do S5 em qualquer porte.

A consequência para o cooperativismo é direta. A cooperativa que ultrapassa o limiar, ou que deixa de usar a metodologia simplificada, passa a calcular capital com a mesma definição, os mesmos requerimentos mínimos, os mesmos ponderadores de risco e as mesmas regras de provisão de um banco comercial. As regras de capital são as das Resoluções 4.192 e 4.193/2013, substituídas em janeiro de 2022 pelas Resoluções 4.955 e 4.958, e a Resolução 2.682/1999 rege a classificação e o provisionamento das operações. Poucos requisitos variam por segmento: os índices de liquidez e o adicional sistêmico valem apenas para o S1, e a razão de alavancagem para S1 e S2. Esses dois segmentos contêm apenas bancos.

{{fig:figures/wp1_metodologia.png|1.0|Figura 1. Instituições por metodologia prudencial, 2017 a 2024|Fonte: elaboração dos autores com dados do IF.data (Banco Central do Brasil). O painel (c) mostra a parcela de instituições na metodologia completa. O degrau de 2023 no painel (b) é a entrada dos conglomerados de instituições de pagamento.}}

### 1.2 O cooperativismo de crédito no sistema financeiro

As cooperativas de crédito são instituições captadoras de depósitos, de propriedade dos associados, que emprestam sobretudo a eles. Organizam-se sob a Lei Complementar 130/2009 e, desde janeiro de 2023, sob a Resolução CMN 5.051/2022, que as classifica em plenas, clássicas e de capital e empréstimo. O segmento detinha cerca de 6% dos ativos do sistema financeiro ao fim de 2024 e 6,3% um ano depois, com participação crescente em todos os anos desde 2020. Boa parte do setor pertence a sistemas integrados, nos quais as centrais fornecem liquidez, gestão consolidada de risco e uma interface única com a supervisão.

### 1.3 Por que a comparação importa

O benchmark prudencial é calibrado na instituição média sob a metodologia completa. Se essa média descreve uma instituição que pouco empresta, a cooperativa que atende a economia local é medida com uma régua feita para outro tipo de negócio. A teoria dá razões para esperar um perfil distinto. O capital da cooperativa é um dote de reservas acumuladas ao longo de gerações de associados, que não pode ser complementado com capital de terceiros com direito a voto. A cota-parte do associado é um direito de uso da instituição, com incentivos limitados para acumular capital além do que o atendimento aos membros exige.

As pesquisas internacionais sobre proporcionalidade registram porte, complexidade e modelo de negócio como critérios em uso, e nenhum baseado na forma organizacional. Onde o supervisor adapta o arcabouço às cooperativas, a adaptação recai sobre o tratamento das cotas como capital e sobre os arranjos das redes. A literatura empírica encontra bancos cooperativos mais estáveis, menos lucrativos e menos capitalizados que bancos comerciais, mas nenhum estudo compara as duas formas sob uma metodologia prudencial comum. O Brasil oferece esse experimento natural.

## 2. O que foi analisado

### 2.1 Dados e amostra

A base é o IF.data, repositório estatístico público do Banco Central. Os relatórios de resumo financeiro, segmentação, composição de ativos e demonstração de resultado foram unidos por instituição e data-base, de 2014 a 2024. As instituições são classificadas pelo tipo de consolidado bancário do próprio regulador, e não pelo nome: o código b3S identifica a cooperativa singular e o b3C a central. As centrais ficam fora da análise, por serem entidades de atacado com capital elevado por razões estruturais. A classificação por nome colocaria os bancos cooperativos Sicredi e Sicoob, ambos bancos comerciais, no grupo das cooperativas.

A amostra reúne todas as instituições na metodologia completa entre o primeiro trimestre de 2017 e o último de 2024: 130 cooperativas singulares e 144 bancos, em 7.234 observações de instituição-trimestre. O grupo de comparação principal são os bancos comerciais e múltiplos com carteira comercial e os bancos múltiplos e de investimento. Outros quatro grupos são usados como parâmetro: todas as não cooperativas, bancos da mesma macrorregião, apenas bancos comerciais e bancos com depósitos em todos os trimestres.

### 2.2 Indicadores

- Índice de Basileia, em pontos percentuais.
- Alavancagem: passivo total sobre ativo total.
- Retorno sobre ativos, anualizado.
- Margem de intermediação sobre o ativo, bruta de provisão.
- Índice custo/receita.
- Carteira de crédito sobre o ativo total.
- Provisão constituída sobre a carteira bruta.
- Captações sobre o ativo total.
- Volatilidade do retorno sobre ativos e z-score, medidos por instituição.

### 2.3 Método

Cada indicador é relacionado a uma variável que identifica a cooperativa, em quatro especificações de rigor crescente: diferença simples de médias; controle por porte (ativo total em logaritmo) e trimestre; pareamento exato com coarsening por quintil de porte, com controle por região; e restrição à faixa de porte em que os dois grupos coexistem. Os erros-padrão são agrupados por instituição e confirmados por um bootstrap apropriado a poucos grupos tratados. Como vários indicadores são assimétricos, a mediana condicional e as regressões quantílicas acompanham a média.

Duas características do IF.data foram corrigidas. As contas de resultado acumulam dentro do semestre e foram desacumuladas e anualizadas. O resultado de intermediação é informado líquido da provisão para créditos de difícil liquidação e foi recomposto bruto dela, para que a margem e o índice de eficiência não repitam o resultado de provisão sob outro nome.

Uma regra explícita classifica cada indicador. O resultado é nulo se não for significativo, com o mesmo sinal, nas quatro especificações. É estável se resistir a todas as regras de winsorização, variar menos que o dobro entre elas e manter, entre o 20º e o 80º percentil, pelo menos metade da magnitude da média. Do contrário, é estável no sinal: a direção se mantém, mas a magnitude depende das caudas.

## 3. Resultados

### 3.1 O perfil da cooperativa

Cinco dos oito indicadores trimestrais mantêm sinal e significância nas quatro especificações e em todas as regras de winsorização. Em porte comparável, a cooperativa destina cerca de um quinto a mais do ativo ao crédito, com diferença ainda maior na mediana. Seu retorno sobre ativos supera o do banco em cerca de dois pontos percentuais, uma diferença grande pelos padrões da literatura bancária. A margem de intermediação é indistinguível da margem bancária, de modo que o retorno maior vem do volume de crédito e do custo menor. A cooperativa opera com custo menor, embora a magnitude dessa diferença dependa das caudas, porque o denominador se aproxima de zero em bancos que pouco intermediam; a mediana condicional, cujo intervalo exclui zero, é a medida mais confiável.

Os retornos da cooperativa também são menos voláteis. Em porte comparável, o desvio-padrão do retorno sobre ativos é menor e o z-score é maior, nas quatro especificações e em todos os grupos nacionais de comparação. A combinação é de retorno mais alto e mais estável, sobre a mesma margem de intermediação.

{{table:t2|Tabela 1. Diferença cooperativa menos bancos, quatro especificações|Erros-padrão agrupados por instituição (HC3 nas duas últimas linhas); * p<0,05, ** p<0,01, *** p<0,001, confirmados por bootstrap. Mediana (2): mediana condicional da coluna (2). Classificação: regra da seção 2.3. Fonte: elaboração dos autores com dados do IF.data.}}

{{fig:figures/wp3_perfil.png|1.0|Figura 2. Todos os indicadores contra bancos, em desvios-padrão de cada indicador|Fonte: elaboração dos autores com dados do IF.data. Especificação com controle de porte e trimestre. Intervalos de 95% agrupados por instituição.}}

### 3.2 Capital: nível e dispersão

O resultado sobre capital exige cuidado na leitura. Sem controles, a cooperativa mediana é mais capitalizada que o banco mediano, e a mediana das cooperativas fica acima da dos bancos na maior parte do período. Com controle de porte, porém, a diferença média é grande e negativa em todas as especificações. A Figura 3 concilia as duas leituras. O coeficiente da cooperativa é positivo na parte inferior da distribuição condicional do índice de Basileia e negativo na parte superior, e cruza zero perto do 40º percentil. Entre o 20º e o 80º percentil, a diferença média é cerca de um terço da diferença na média condicional.

A média é puxada por uma cauda superior própria dos bancos. Sem controles, 14% dos trimestres bancários apresentam índice de Basileia acima de 50%, contra 1% dos trimestres das cooperativas. Essa cauda se concentra nos bancos que reportam individualmente, pequenos e com pouca exposição ponderada pelo risco. Exigir que o banco capte depósitos em todos os trimestres reduz à metade tanto a parcela de trimestres acima de 50% quanto a diferença média estimada. Em porte igual, o que separa os dois grupos é sobretudo a dispersão: descontados porte e trimestre, o desvio-padrão do índice de capital entre cooperativas é cerca de um terço do observado entre bancos. O mesmo padrão vale para os demais indicadores. As cooperativas formam o grupo mais homogêneo em todos eles, com dispersão residual entre um décimo e a metade da dos bancos.

{{fig:figures/wp2_capital.png|1.0|Figura 3. O índice de Basileia ao longo da distribuição|Fonte: elaboração dos autores com dados do IF.data. Painel (a): coeficientes de regressão quantílica com faixa de 95% por bootstrap de instituições, e a média condicional. Painel (b): índice antes da winsorização, em escala logarítmica; as alturas são percentuais dos trimestres de cada grupo.}}

### 3.3 Duas diferenças que desaparecem

Contra todas as não cooperativas, a cooperativa parece provisionar menos, com significância a 1% nas quatro especificações. Contra bancos, o coeficiente fica próximo de zero. A diferença do grupo amplo vem das instituições não bancárias que emprestam, cujos índices de provisão são quase três vezes os de bancos e cooperativas. Na mediana condicional o sinal se inverte, com a cooperativa provisionando mais. Como a preocupação da supervisão recai sobre o capital, a amostra foi dividida em tercis do índice de Basileia: nenhum tercil mostra a cooperativa provisionando menos. Como a provisão mínima é uma função da classificação de risco AA a H de cada operação, o resultado descreve sobretudo como cada grupo classifica sua carteira.

A margem de intermediação segue o mesmo padrão. Contra o grupo amplo, ela é grande e significativa, porque as instituições não bancárias reportam margens várias vezes maiores que as de bancos e cooperativas em relação ao ativo. Contra bancos, é pequena e não significativa; contra bancos com depósitos, torna-se positiva. Como o sinal depende do grupo de comparação, o indicador é classificado como nulo. O índice de captações é significativo em uma das quatro especificações e inverte o sinal na mediana, e também não é reportado como resultado.

{{fig:figures/wp4_grupos.png|1.0|Figura 4. Quatro indicadores ao longo dos cinco grupos de comparação|Fonte: elaboração dos autores com dados do IF.data. Especificação com controles; o grupo "mesma região" pareia também por macrorregião. Intervalos de 95% agrupados por instituição. Marcadores cheios: p < 0,05. Faixa sombreada: bancos, o grupo principal.}}

### 3.4 Dentro e fora dos mercados regionais

Pareada apenas por porte, a cooperativa destina ao crédito parcela substancialmente maior do ativo que o banco comparável, com significância a 1% em todas as especificações. Pareada também por macrorregião, a diferença é pequena e não se distingue de zero. As cooperativas emprestam mais que o conjunto nacional de bancos; dentro dos mercados regionais, a diferença não pode ser separada de zero. Qual das duas estimativas é a relevante depende de uma hipótese que os dados não testam. Se a cooperativa se concentra onde está por razões internas ao modelo de finanças associativas, a região é um mediador e vale a estimativa nacional. Se a estrutura do mercado regional é alheia à forma organizacional, a região é um fator de confusão e o resultado é nulo. O estudo reporta as duas como parâmetros distintos. As estimativas regionais são imprecisas, porque o pareamento exato por região deixa um conjunto de controle efetivo de cerca de dezoito instituições.

### 3.5 Redes

Sicredi e Sicoob respondem por todas as cooperativas da amostra, exceto sete. As cooperativas das duas redes mantêm menos capital regulatório que bancos comparáveis, com significância confirmada pelo bootstrap em cada uma. As seis independentes se apoiam em cinco grupos tratados, e sua estimativa de capital é positiva e indistinguível de ruído. A divisão localiza a diferença de capital nas duas grandes redes sem explicá-la. Um mecanismo de proteção da rede é uma explicação candidata: uma cooperativa com liquidez centralizada e gestão consolidada de risco atrás de si pode operar com um colchão individual mais fino. As redes também diferem em porte, geografia, mix de negócios e governança das filiadas, e a divisão não separa a proteção desses fatores. A provisão é não significativa em todos os sistemas.

### 3.6 Testes de sensibilidade

- Excluir os onze bancos de S1 e S2 altera nenhum coeficiente significativo em mais de 2%.
- Todos os resultados mantêm sinal e significância antes e depois da revisão das regras de capital de janeiro de 2022, com magnitudes cerca de um quinto menores no segundo período.
- Quatro regras de winsorização, a reestimação apenas nas linhas com provisão observada e a exclusão das seis cooperativas que retornaram à metodologia simplificada deixam todos os sinais inalterados.
- As estimativas pareadas, ponderadas e não ponderadas, diferem menos que o erro amostral.
- As cooperativas que adotam a metodologia completa durante o período eram, antes da adoção, menos intensivas em crédito e marginalmente menos lucrativas que as que nunca adotam. A seleção para a amostra tende a reduzir, e não a inflar, as diferenças de crédito e rentabilidade.

## 4. O que os resultados significam

### 4.1 Para a regulação proporcional

Os resultados tocam dois eixos de proporcionalidade além do porte. O primeiro é a arquitetura organizacional. A diferença de capital é uma propriedade das duas grandes redes. Se a hipótese da proteção de rede estiver correta, um arcabouço proporcional pode tratar a rede integrada e seu mecanismo de proteção como a unidade relevante para parte da avaliação de capital e liquidez. Os grupos cooperativos franceses já são tratados assim. Se a diferença refletir porte, geografia ou mix das filiadas, a sugestão não se sustenta. O segundo eixo é a calibragem do benchmark. Um referencial definido pela instituição média da metodologia completa pode descrever mal a configuração cooperativa, porque essa média vem de uma distribuição cuja região superior as cooperativas não ocupam.

Um requerimento mais leve não decorre automaticamente desses achados. O argumento de que o supervisor age em nome de depositantes dispersos perde força para uma cooperativa de propriedade dos associados e monitorada pela rede. A externalidade sistêmica da quebra e o risco moral da garantia pública continuam a valer. Capital mais fino pode pedir atenção supervisória mais próxima, e não apenas alívio.

### 4.2 Para a supervisão

A combinação relevante é capital e provisão lidos em conjunto. Na ponta fina da distribuição de capital, onde a preocupação prudencial se concentra, a cooperativa mantém mais capital que o banco comparável e provisiona igual ou mais. O dado que sustenta a leitura de "cooperativa menos capitalizada" é a ausência, entre cooperativas, da cauda de bancos muito capitalizados. Várias diferenças que parecem grandes na média são diferenças de dispersão, e a mediana condicional e o perfil por quantil merecem o mesmo peso que a média.

### 4.3 Para o Sistema OCB e as cooperativas

A diferença entre as duas formas persiste sob uma metodologia prudencial comum, em versão mais estreita do que uma comparação frouxa sugere. O posicionamento institucional ganha em precisão se apoiado nos resultados que resistiram a todas as definições de banco testadas: custo menor na mediana, retorno sobre ativos maior e retorno mais estável. O argumento de provisionamento mais conservador que o dos bancos não encontra apoio nos dados. O argumento de maior intensidade de crédito vale contra o conjunto nacional de bancos e ainda não foi demonstrado dentro dos mercados regionais.

Três escolhas de análise decidiram se os resultados de manchete existiam: o grupo de comparação, a leitura das contas de resultado como fluxos trimestrais e a estimação não ponderada na amostra pareada. Cada uma é uma leitura natural do material de origem, e parte das divergências na literatura pode refletir grupos de comparação distintos.

## 5. Limites do estudo

- Como a condição de cooperativa não varia no tempo, as estimativas são correlações condicionais, não efeitos causais da forma organizacional.
- A restrição à metodologia completa seleciona as maiores cooperativas, cerca de um décimo das registradas no painel, e os resultados valem para essa subpopulação.
- O índice de provisão é uma variável contábil e não mede inadimplência.
- Os indicadores de estabilidade são estatísticas por instituição, estimadas sem efeitos de trimestre, em uma subamostra com ao menos oito trimestres.
- A maioria dos sistemas é pouco representada para inferência separada, e a hipótese da proteção de rede exige dados consolidados que o IF.data não traz.
- A macrorregião é uma medida grosseira de mercado; a distinção relevante é provavelmente o crédito rural.

## 6. Recomendações

1. Levar ao Banco Central a discussão sobre o tratamento das redes integradas e de seus mecanismos de proteção na avaliação de capital e liquidez, com a experiência francesa como referência.
2. Apoiar o posicionamento institucional nos resultados que resistiram a todas as comparações: custo, retorno e estabilidade.
3. Evitar o argumento de provisionamento mais conservador que o dos bancos, que os dados não sustentam.
4. Estender a análise com os módulos de modalidade de crédito do IF.data, para testar a diferença de intensidade de crédito dentro dos mercados regionais.
5. Reunir dados consolidados das redes para testar a hipótese da proteção de rede.
6. Atualizar o estudo anualmente com o pipeline público de reprodução e acompanhar os efeitos da revisão das regras de capital de 2022 e da Resolução 4.966/2021.

## Anexo. Nota metodológica

Os resultados vêm de um único conjunto de scripts executado sobre os arquivos públicos do IF.data, com cada grupo de comparação, esquema de coarsening, regra de winsorização e teste de sensibilidade tratado como parâmetro. As tabelas e figuras são geradas a partir dos arquivos de resultado, sem transcrição manual. A reprodução completa do pipeline a partir de um diretório vazio devolve todos os arquivos de resultado, tabelas e figuras byte a byte.

O estimador de pareamento pondera as unidades de controle para que a razão entre tratados e controles seja igual em cada estrato; a regressão simples na amostra pareada não recupera esse estimando, e os dois são reportados. A inferência usa erros-padrão agrupados por instituição e um bootstrap selvagem restrito com pesos de Rademacher, porque o teste agrupado rejeita uma hipótese nula verdadeira em 16% das simulações com seis grupos tratados, contra o nível nominal de 5%. Os indicadores de estabilidade são estimados com uma linha por instituição, com a média do logaritmo do ativo como controle de porte.

Este documento resume o artigo "Institutional Profiles Under a Common Prudential Framework: Evidence from Brazilian Credit Cooperatives and Banks", dos mesmos autores, submetido à ICA CCR Europe Research Conference 2026 (Valência, 3 a 6 de novembro de 2026). O artigo contém a descrição completa dos dados, das especificações e dos testes.

## Referências selecionadas

{{refs:bcbs2011, bcbs2019, bcb2026panorama, cmn4553, cmn4606, cmn5051, coelho2019, fonteyne2007, hesse2007, mckillop2020, iacus2012, cameron2008}}
