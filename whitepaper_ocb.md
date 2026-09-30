# Cooperativas de crédito e bancos sob a mesma régua prudencial

> O que os dados do Banco Central revelam sobre o perfil das cooperativas enquadradas na metodologia completa de Basileia, 2017 a 2024
> Whitepaper. Sistema OCB, setembro de 2026.
> Arthur Gomes Nery, Thiago de Oliveira Victorino e Rodrigo Lima Rangel

<!-- Fonte do whitepaper em português. make_docx.py whitepaper gera o .docx no modelo de
     Briefing do Sistema OCB. Marcações: # título, > subtítulo, ## seção, ### subseção,
     - lista, 1. lista numerada, {{fig:...}}, {{table:t2|...}}, {{refs:...}}, {{pagebreak}}.
     Todos os números vêm do artigo e das tabelas geradas pelo pipeline. -->

## Sumário executivo

- Desde 2017, a cooperativa de crédito cujo porte supera 0,1% do PIB, ou que opta por deixar o regime simplificado, apura capital, riscos e provisões pelas mesmas regras aplicadas a um banco comercial.
- Este estudo compara 130 cooperativas singulares e 144 bancos nessa situação, com dados públicos do IF.data de 2017 a 2024, controlando o porte das instituições.
- Em relação a bancos de porte semelhante, as cooperativas destinam parcela maior do ativo ao crédito, obtêm retorno sobre o ativo mais alto, operam com custo menor e apresentam retornos mais estáveis.
- A diferença de capital é moderada em nível e grande em dispersão: as cooperativas se concentram em uma faixa estreita do índice de Basileia e não apresentam a cauda de bancos pequenos com índices acima de 50%.
- Duas diferenças citadas com frequência, o menor provisionamento e a margem mais estreita, desaparecem quando a comparação se restringe aos bancos.
- Para a regulação proporcional, os resultados indicam duas dimensões além do porte: o tratamento dos sistemas cooperativos e a calibragem do referencial prudencial. Um alívio regulatório não decorre automaticamente desses resultados.

## 1. Contexto

### 1.1 Um mesmo conjunto de regras

A regulação prudencial convergiu para um modelo único. O acordo de Basileia III define a estrutura de capital, de alavancagem e de mensuração de riscos, e cada supervisor nacional a adapta às condições locais. No Brasil, a Resolução CMN 4.553/2017 enquadra as instituições autorizadas a funcionar em cinco segmentos, conforme o porte e a relevância da atividade internacional. Os segmentos S1 a S4 aplicam a metodologia completa. O S5 é composto pelas instituições de porte inferior a 0,1% do PIB que optam pela metodologia facultativa simplificada de apuração dos requerimentos mínimos de capital (Resolução CMN 4.606/2017). Bancos comerciais, múltiplos, de investimento e de câmbio não podem integrar o S5, qualquer que seja o porte.

Para o cooperativismo de crédito, a consequência é direta. A cooperativa que ultrapassa esse limite, ou que deixa de adotar a metodologia simplificada, passa a apurar seu capital regulamentar como um banco comercial. Valem para ela a mesma definição de Patrimônio de Referência, os mesmos requerimentos mínimos, os mesmos fatores de ponderação de risco e as mesmas regras de provisionamento. As regras de capital são as das Resoluções CMN 4.192 e 4.193/2013, substituídas em janeiro de 2022 pelas Resoluções 4.955 e 4.958, e a classificação e o provisionamento das operações de crédito seguem a Resolução CMN 2.682/1999. Poucas exigências variam entre os segmentos: os índices de liquidez e o adicional de importância sistêmica aplicam-se apenas ao S1, e a razão de alavancagem, ao S1 e ao S2. Esses dois segmentos são formados exclusivamente por bancos.

{{fig:figures/wp1_metodologia.png|1.0|Figura 1. Instituições por metodologia prudencial, 2017 a 2024|Fonte: elaboração dos autores com dados do IF.data (Banco Central do Brasil). O painel (c) mostra a parcela de instituições enquadradas na metodologia completa. O degrau de 2023 no painel (b) corresponde à entrada dos conglomerados liderados por instituições de pagamento.}}

### 1.2 O cooperativismo de crédito no Sistema Financeiro Nacional

As cooperativas de crédito são instituições financeiras captadoras de depósitos, de propriedade de seus associados, cuja carteira de crédito se destina majoritariamente a eles. São regidas pela Lei Complementar 130/2009 e, desde janeiro de 2023, pela Resolução CMN 5.051/2022, que as classifica em plenas, clássicas e de capital e empréstimo. O segmento respondia por cerca de 6% dos ativos do Sistema Financeiro Nacional ao final de 2024 e por 6,3% em dezembro de 2025, com participação crescente em todos os anos desde 2020. A maior parte das singulares é filiada a sistemas cooperativos, nos quais as centrais oferecem centralização financeira, gestão consolidada de riscos e um canal único de relacionamento com a supervisão.

### 1.3 Por que a comparação importa

O referencial prudencial é calibrado pela instituição média enquadrada na metodologia completa. Se essa média descreve uma instituição que pouco empresta, a cooperativa que atende à economia local é avaliada por um padrão construído para outro tipo de negócio. A teoria econômica das cooperativas oferece razões para esperar um perfil distinto. O capital da cooperativa é formado por reservas acumuladas ao longo de gerações de associados, um patrimônio sem dono final, que não pode ser reforçado com aportes de investidores externos com direito a voto. A cota-parte do associado é um direito de uso dos serviços da instituição, e os incentivos para acumular capital além do necessário ao atendimento dos cooperados são limitados.

Os levantamentos internacionais sobre proporcionalidade apontam porte, complexidade e modelo de negócios como os critérios adotados pelos supervisores; nenhum deles considera a forma organizacional. Onde o supervisor adapta o arcabouço às cooperativas, a adaptação recai sobre o tratamento das cotas-partes como capital e sobre os arranjos dos sistemas. A literatura empírica internacional indica que os bancos cooperativos são mais estáveis, menos rentáveis e menos capitalizados que os bancos comerciais. Nenhum desses estudos, porém, compara as duas formas de organização sob uma metodologia prudencial comum. O Brasil oferece esse experimento natural.

## 2. O que foi analisado

### 2.1 Dados e amostra

Os dados provêm do IF.data, base pública de informações das instituições financeiras divulgada pelo Banco Central do Brasil. Os relatórios de resumo, de segmentação, de composição do ativo e de demonstração de resultado foram combinados por instituição e data-base, de 2014 a 2024. A classificação das instituições segue o tipo de consolidado bancário definido pelo próprio regulador: o código b3S identifica as cooperativas singulares e o b3C, as centrais e confederações. As centrais foram excluídas da análise, por serem entidades de segundo grau, que prestam serviços de centralização financeira e de gestão de riscos às filiadas e mantêm capital elevado por razões estruturais. Uma classificação pelo nome colocaria o Banco Cooperativo Sicredi e o Banco Sicoob, ambos bancos comerciais, no grupo das cooperativas.

A amostra abrange todas as instituições enquadradas na metodologia completa entre o primeiro trimestre de 2017 e o quarto trimestre de 2024: 130 cooperativas singulares e 144 bancos, em 7.234 observações trimestrais. O grupo de comparação principal reúne os bancos comerciais, os bancos múltiplos com carteira comercial e os bancos múltiplos sem carteira comercial e de investimento. Outros quatro grupos servem de contraponto: todas as instituições não cooperativas, os bancos da mesma macrorregião, apenas os bancos comerciais e os bancos que captaram depósitos em todos os trimestres do período.

### 2.2 Indicadores

- Índice de Basileia, em pontos percentuais.
- Alavancagem: razão entre o passivo total e o ativo total.
- Retorno sobre o ativo (ROA), anualizado.
- Margem de intermediação financeira sobre o ativo, antes das despesas de provisão.
- Índice de eficiência: despesas de pessoal e administrativas sobre as receitas.
- Operações de crédito sobre o ativo total.
- Provisão para créditos de liquidação duvidosa sobre a carteira de crédito.
- Captações de recursos sobre o ativo total.
- Volatilidade do ROA e z-score, calculados por instituição ao longo do período.

### 2.3 Método

Para cada indicador, estima-se a diferença entre cooperativas e bancos em quatro especificações de rigor crescente: a diferença simples de médias; o controle por porte (logaritmo do ativo total) e por trimestre; o pareamento exato por faixas de porte, com controle por região; e a restrição à faixa de porte em que os dois grupos se sobrepõem. Os erros-padrão são agrupados por instituição, e a significância é confirmada por um procedimento de bootstrap adequado a amostras com poucos grupos tratados. Como a distribuição de vários indicadores é assimétrica, a mediana condicional e as regressões quantílicas são apresentadas ao lado da média.

Dois ajustes foram feitos nos dados do IF.data. As contas de resultado são acumuladas dentro do semestre, porque as instituições levantam balanço em junho e dezembro; os valores foram desacumulados e anualizados. O resultado de intermediação financeira é informado líquido das despesas de provisão para créditos de liquidação duvidosa e foi recomposto antes dessas despesas, para que a margem e o índice de eficiência não reproduzam o resultado de provisão sob outra denominação.

Cada indicador recebe uma classificação segundo regra explícita. O resultado é considerado nulo quando a diferença não é significativa, com o mesmo sinal, nas quatro especificações. É considerado estável quando se mantém significativo sob todas as regras de tratamento de valores extremos, varia menos que o dobro entre elas e conserva, entre o 20º e o 80º percentil, ao menos metade da magnitude estimada na média. Nos demais casos, é estável apenas no sinal: a direção da diferença se mantém, mas a magnitude depende das caudas da distribuição.

## 3. Resultados

### 3.1 O perfil da cooperativa

Cinco dos oito indicadores trimestrais mantêm sinal e significância nas quatro especificações e em todas as regras de tratamento de valores extremos. Em porte comparável, as cooperativas destinam às operações de crédito uma parcela do ativo cerca de um quinto maior que a dos bancos, e a diferença é ainda maior na mediana. O retorno sobre o ativo supera o dos bancos em cerca de dois pontos percentuais, diferença expressiva para os padrões da literatura bancária. A margem de intermediação não difere da dos bancos, de modo que o retorno maior decorre do volume de crédito e do menor custo operacional. As cooperativas operam com custo menor, embora a magnitude dessa diferença dependa dos valores extremos, já que o denominador do índice se aproxima de zero em bancos com pouca intermediação. A mediana condicional, cujo intervalo de confiança exclui zero, é a medida mais confiável.

Os retornos das cooperativas também oscilam menos. Em porte comparável, o desvio-padrão do ROA é menor e o z-score é maior, nas quatro especificações e em todos os grupos nacionais de comparação. O quadro é de retorno mais alto e mais estável, obtido sobre a mesma margem de intermediação.

{{table:t2|Tabela 1. Diferença entre cooperativas e bancos em quatro especificações|Erros-padrão agrupados por instituição (HC3 nas duas últimas linhas); * p<0,05, ** p<0,01, *** p<0,001, confirmados por bootstrap. Mediana (2): mediana condicional da especificação (2). Classificação: regra da seção 2.3. Fonte: elaboração dos autores com dados do IF.data.}}

{{fig:figures/wp3_perfil.png|1.0|Figura 2. Diferença entre cooperativas e bancos em cada indicador, em desvios-padrão|Fonte: elaboração dos autores com dados do IF.data. Especificação com controle de porte e trimestre. Intervalos de confiança de 95%, com erros-padrão agrupados por instituição.}}

### 3.2 Capital: nível e dispersão

O resultado relativo ao capital exige leitura cuidadosa. Sem controles, a cooperativa mediana apresenta índice de Basileia superior ao do banco mediano, e a mediana das cooperativas supera a dos bancos na maior parte do período. Quando se controla o porte, porém, a diferença de médias é grande e negativa em todas as especificações. A Figura 3 concilia as duas leituras. A diferença estimada é positiva na parte inferior da distribuição condicional do índice de Basileia e negativa na parte superior, com inversão de sinal próxima ao 40º percentil. Entre o 20º e o 80º percentil, a diferença média corresponde a cerca de um terço da estimada pela média condicional.

A média é influenciada por uma cauda superior que só existe entre os bancos. Em 14% das observações trimestrais dos bancos, o índice de Basileia supera 50%; entre as cooperativas, essa proporção é de 1%. Essa cauda se concentra em bancos pequenos, que reportam de forma individual e têm baixa exposição ponderada pelo risco. Quando a comparação se restringe aos bancos que captaram depósitos em todos os trimestres, tanto a proporção de observações acima de 50% quanto a diferença média estimada caem à metade. Em porte igual, o que distingue os dois grupos é sobretudo a dispersão. Descontados os efeitos de porte e de trimestre, o desvio-padrão do índice de Basileia entre as cooperativas equivale a cerca de um terço do observado entre os bancos. O padrão se repete nos demais indicadores: as cooperativas formam o grupo mais homogêneo em todos eles, com dispersão residual entre um décimo e a metade da observada nos bancos.

{{fig:figures/wp2_capital.png|1.0|Figura 3. O índice de Basileia ao longo da distribuição|Fonte: elaboração dos autores com dados do IF.data. Painel (a): coeficientes de regressão quantílica, com faixa de confiança de 95% obtida por bootstrap de instituições, e a média condicional. Painel (b): índice de Basileia antes do tratamento de valores extremos, em escala logarítmica; as alturas indicam o percentual das observações trimestrais de cada grupo.}}

### 3.3 Duas diferenças que desaparecem

Em comparação com o conjunto de todas as instituições não cooperativas, as cooperativas parecem provisionar menos, com significância a 1% nas quatro especificações. Em comparação com os bancos, a diferença fica próxima de zero. A diferença observada no grupo amplo decorre das instituições não bancárias que concedem crédito, cujos índices de provisionamento são quase três vezes os de bancos e cooperativas. Na mediana condicional, o sinal se inverte: as cooperativas provisionam mais. Como a atenção da supervisão recai sobre o capital, a amostra foi dividida em tercis do índice de Basileia. Em nenhum deles as cooperativas provisionam menos que os bancos. Como a provisão mínima decorre da classificação de risco de cada operação, de AA a H, conforme a Resolução 2.682/1999, o resultado reflete sobretudo a forma como cada grupo classifica sua carteira.

A margem de intermediação segue o mesmo padrão. No grupo amplo, a diferença é grande e significativa, porque as instituições não bancárias registram margens várias vezes superiores às de bancos e cooperativas em relação ao ativo. Em comparação com os bancos, a diferença é pequena e não significativa; em comparação com os bancos que captam depósitos, torna-se positiva. Como o sinal depende do grupo de comparação, o indicador é classificado como nulo. O índice de captações é significativo em apenas uma das quatro especificações e muda de sinal na mediana, razão pela qual também não é tratado como resultado.

{{fig:figures/wp4_grupos.png|1.0|Figura 4. Quatro indicadores nos cinco grupos de comparação|Fonte: elaboração dos autores com dados do IF.data. Especificação com controle de porte e trimestre; o grupo "mesma região" pareia também por macrorregião. Intervalos de confiança de 95%, com erros-padrão agrupados por instituição. Marcadores cheios: p < 0,05. Faixa sombreada: bancos, o grupo principal.}}

### 3.4 Dentro e fora dos mercados regionais

Quando o pareamento considera apenas o porte, as cooperativas destinam ao crédito parcela do ativo substancialmente maior que a dos bancos comparáveis, com significância a 1% em todas as especificações. Quando o pareamento inclui também a macrorregião, a diferença é pequena e não se distingue de zero. As cooperativas emprestam mais que o conjunto dos bancos do país; dentro de cada mercado regional, a diferença não pode ser separada de zero. Qual das duas estimativas é a relevante depende de uma hipótese que os dados não permitem testar. Se a cooperativa se concentra onde está por razões internas ao modelo de finanças associativas, a região é um mediador e vale a estimativa nacional. Se a estrutura do mercado regional independe da forma organizacional, a região é um fator de confusão e o resultado é nulo. O estudo apresenta as duas estimativas como parâmetros distintos. As estimativas regionais são imprecisas, porque o pareamento exato por região reduz o grupo de controle efetivo a cerca de dezoito instituições.

### 3.5 Sistemas cooperativos

Sicredi e Sicoob reúnem todas as cooperativas da amostra, com exceção de sete. As filiadas aos dois sistemas mantêm índice de Basileia inferior ao de bancos comparáveis, com significância confirmada pelo bootstrap em cada um deles. As seis cooperativas independentes correspondem a apenas cinco grupos tratados, e a diferença de capital estimada para elas é positiva e não se distingue de ruído estatístico. A divisão por sistema localiza a diferença de capital nos dois grandes sistemas, mas não a explica. Uma explicação possível é o suporte do sistema: uma cooperativa que conta com centralização financeira e gestão consolidada de riscos pode operar com um colchão individual mais fino. Os sistemas também diferem quanto ao porte, à distribuição geográfica, ao perfil de negócios e à governança das filiadas, e a análise não separa o efeito do suporte desses fatores. A diferença de provisionamento não é significativa em nenhum dos sistemas.

### 3.6 Testes de sensibilidade

- A exclusão dos onze bancos dos segmentos S1 e S2 não altera nenhum coeficiente significativo em mais de 2%.
- Todos os resultados mantêm sinal e significância antes e depois da revisão das regras de capital de janeiro de 2022, com magnitudes cerca de um quinto menores no segundo período.
- Quatro regras de tratamento de valores extremos, a reestimação apenas com as observações em que a provisão é informada e a exclusão das seis cooperativas que voltaram à metodologia simplificada mantêm todos os sinais.
- As estimativas na amostra pareada, com e sem ponderação, diferem entre si menos que o erro amostral.
- As cooperativas que passaram à metodologia completa durante o período tinham, antes da mudança, menor participação do crédito no ativo e rentabilidade um pouco menor que as que permaneceram na simplificada. A seleção para a amostra tende, portanto, a subestimar as diferenças de crédito e de rentabilidade.

## 4. O que os resultados significam

### 4.1 Para a regulação proporcional

Os resultados alcançam duas dimensões da proporcionalidade além do porte. A primeira é a arquitetura organizacional, já que a diferença de capital é um traço dos dois grandes sistemas. Se a hipótese do suporte do sistema se confirmar, um arcabouço proporcional pode tratar o sistema cooperativo e seus mecanismos de proteção como a unidade de referência para parte da avaliação de capital e de liquidez, como já ocorre com os grupos cooperativos franceses. Se a diferença refletir o porte, a distribuição geográfica ou o perfil de negócios das filiadas, essa sugestão perde fundamento. A segunda dimensão é a calibragem do referencial. Um parâmetro definido pela instituição média da metodologia completa pode descrever mal a configuração das cooperativas, porque essa média provém de uma distribuição cuja parte superior as cooperativas não ocupam.

Um requerimento mais brando não decorre automaticamente desses resultados. O argumento de que o supervisor atua em nome de depositantes dispersos perde força no caso de uma cooperativa de propriedade dos associados e acompanhada pela central. O risco sistêmico de uma quebra e o risco moral associado à garantia pública de depósitos permanecem. Um capital mais fino pode justificar tanto acompanhamento supervisório mais próximo quanto alívio de exigências.

### 4.2 Para a supervisão

Para a supervisão, a leitura relevante combina capital e provisão. Na faixa inferior da distribuição de capital, onde se concentra a preocupação prudencial, as cooperativas mantêm mais capital que os bancos comparáveis e provisionam em nível igual ou superior. O dado que sustenta a leitura de que a cooperativa é menos capitalizada é a ausência, entre elas, da cauda de bancos com capital muito elevado. Várias diferenças que parecem grandes na média são, na verdade, diferenças de dispersão; a mediana condicional e o perfil por quantil merecem o mesmo peso que a média na análise.

### 4.3 Para o Sistema OCB e as cooperativas

As diferenças entre as duas formas de organização persistem sob a metodologia prudencial comum, ainda que em versão mais restrita do que sugere uma comparação menos criteriosa. O posicionamento institucional ganha precisão quando se apoia nos resultados que resistiram a todas as definições de banco testadas: menor custo na mediana, maior retorno sobre o ativo e retorno mais estável. O argumento de que as cooperativas provisionam de forma mais conservadora que os bancos não encontra apoio nos dados. O argumento da maior participação do crédito no ativo vale em relação ao conjunto dos bancos do país, mas ainda não foi demonstrado dentro dos mercados regionais.

Três decisões de análise determinaram a existência ou não dos resultados de destaque: a escolha do grupo de comparação, a leitura das contas de resultado como fluxos trimestrais e a estimação sem ponderação na amostra pareada. Cada uma delas é uma leitura natural dos dados originais, e parte das divergências encontradas na literatura pode refletir grupos de comparação distintos.

## 5. Limites do estudo

- Como a condição de cooperativa não varia no tempo, as estimativas são correlações condicionais e não devem ser lidas como efeitos causais da forma organizacional.
- A restrição à metodologia completa seleciona as maiores cooperativas, cerca de um décimo das registradas no painel, e os resultados se aplicam a essa subpopulação.
- O índice de provisionamento é uma variável contábil e não mede a inadimplência efetiva.
- Os indicadores de estabilidade são estatísticas calculadas por instituição, sem controle por trimestre, em uma subamostra com pelo menos oito trimestres de dados.
- A maioria dos sistemas tem poucas cooperativas na amostra para inferência separada, e a hipótese do suporte do sistema exige dados consolidados que o IF.data não contém.
- A macrorregião é uma aproximação grosseira do mercado relevante; a distinção provavelmente mais importante é a do crédito rural.

## 6. Recomendações

1. Levar ao Banco Central a discussão sobre o tratamento dos sistemas cooperativos e de seus mecanismos de proteção na avaliação de capital e de liquidez, tendo a experiência francesa como referência.
2. Apoiar o posicionamento institucional nos resultados que resistiram a todas as comparações: custo, retorno e estabilidade.
3. Evitar o argumento de provisionamento mais conservador que o dos bancos, que os dados não sustentam.
4. Ampliar a análise com os relatórios de carteira de crédito por modalidade do IF.data, para testar a diferença de participação do crédito dentro dos mercados regionais.
5. Reunir dados consolidados dos sistemas cooperativos para testar a hipótese do suporte do sistema.
6. Atualizar o estudo anualmente, com a rotina pública de reprodução, e acompanhar os efeitos da revisão das regras de capital de 2022 e da Resolução CMN 4.966/2021.

## Anexo. Nota metodológica

Os resultados provêm de um único conjunto de rotinas executado sobre os arquivos públicos do IF.data, em que cada grupo de comparação, faixa de pareamento, regra de tratamento de valores extremos e teste de sensibilidade é um parâmetro. As tabelas e figuras são geradas diretamente dos arquivos de resultado, sem transcrição manual. A reexecução completa das rotinas a partir de um diretório vazio reproduz todos os arquivos de resultado, tabelas e figuras de forma idêntica.

O estimador de pareamento pondera as unidades de controle de modo que a razão entre tratados e controles seja a mesma em cada estrato. A regressão simples na amostra pareada não recupera esse estimando, e por isso os dois são apresentados. A inferência utiliza erros-padrão agrupados por instituição e um bootstrap selvagem restrito com pesos de Rademacher. Em simulações com seis grupos tratados, o teste agrupado convencional rejeita uma hipótese nula verdadeira em 16% dos casos, contra o nível nominal de 5%. Os indicadores de estabilidade são estimados com uma observação por instituição, tendo a média do logaritmo do ativo como controle de porte.

Este documento resume o artigo "Institutional Profiles Under a Common Prudential Framework: Evidence from Brazilian Credit Cooperatives and Banks", dos mesmos autores, submetido à ICA CCR Europe Research Conference 2026 (Valência, 3 a 6 de novembro de 2026). O artigo contém a descrição completa dos dados, das especificações e dos testes.

## Referências selecionadas

{{refs:bcbs2011, bcbs2019, bcb2026panorama, cmn4553, cmn4606, cmn5051, coelho2019, fonteyne2007, hesse2007, mckillop2020, iacus2012, cameron2008}}
