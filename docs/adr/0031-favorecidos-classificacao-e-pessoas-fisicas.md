# ADR-0031: Favorecidos — classificação, identificação e pessoas físicas

- **Estado:** aceito (2026-11-22). A publicação de pessoas físicas foi decidida pelo
  mantenedor (D3), e o `noindex` (5.6) aprovado na D3.1.
- **Contexto normativo:** CLAUDE.md §9.4, §15.3, §23 e §28.5 ("publicar dados restritos"
  exige aprovação, concedida aqui); ADR-0030.

## Contexto

O código do favorecido tem formatos distintos, e a soma sem classificação não tem
significado. Medido em 2025-10, na lente B (766.078 linhas):

| Formato do código | Linhas | R$ bi | O que é |
|---|---:|---:|---|
| CNPJ (14 dígitos) | 224.204 | 82,93 | entes, fundos, empresas, entidades e bancos |
| 6 dígitos | 1.884 | 48,41 | unidade gestora federal: fluxo dentro da União |
| `EX…` | 3.527 | 2,07 | exterior |
| `***.NNN.NNN-**` | 534.863 | 0,83 | pessoa física com CPF mascarado na fonte |
| `RB…`, `TN…`, `PF…`, `-11`, `-1` | 1.586 | −32,10 | lançamentos agregados, PF sem CPF, sigiloso, sem informação |

- **Natureza jurídica.** O cadastro "Favorecidos PJ" da CGU (instantâneo mensal) cobriu 100%
  dos CNPJs favorecidos da amostra. Ele também explica o tipo "Administração Pública" sem
  esfera da lente A: são fundos públicos (1333 Fundo Público da Administração Direta
  Municipal, R$ 14,94 bi; 1325 estadual/DF, R$ 3,90 bi).
- **O CPF mascarado não identifica a pessoa.** Na amostra há 399.818 códigos mascarados
  distintos, e 97.218 deles aparecem com mais de um nome. O mesmo código, na mesma UG,
  aparece em municípios diferentes.

**Base legal da publicação de pessoas físicas** (textos conferidos no Planalto em
2026-11-22):

- **LRF, art. 48-A, I** (incluído pela LC nº 131/2009): manda disponibilizar "à pessoa
  física ou jurídica beneficiária do pagamento";
- **LAI (Lei nº 12.527/2011), art. 8º, § 1º, II e III:** registros de repasses,
  transferências e despesas;
- **LGPD (Lei nº 13.709/2018), art. 7º:**
  - § 3º: o tratamento de dado de acesso público considera "a finalidade, a boa-fé e o
    interesse público que justificaram sua disponibilização";
  - § 7º: permite o tratamento posterior "desde que observados os propósitos legítimos e
    específicos" e preservados os direitos do titular;
  - § 6º: a dispensa de consentimento não desobriga das demais obrigações.

## Decisões

1. **Classe do favorecido** (regra versionada, aplicada na Silver; a ordem resolve
   conflitos):

   | Classe | Regra |
   |---|---|
   | Lançamento agregado do Tesouro ou da rede bancária | prefixo `TN` ou `RB` |
   | Unidade gestora federal | código de 6 dígitos |
   | Sigiloso | `-11` (nome "Sigiloso") |
   | Sem informação | `-1` |
   | Exterior | prefixo `EX` |
   | Pessoa física sem CPF | prefixo `PF` |
   | Pessoa física | `***.NNN.NNN-**` |
   | Município (prefeitura) | CNPJ na TABMUN (ADR-0032) ou natureza 1244 |
   | Estado ou DF | natureza 1236 (estado/DF) ou tipo de favorecido estadual na lente A |
   | Fundo público municipal / estadual ou DF / federal | natureza 1333 ou 1309 / 1325 ou 1295 / 1317 ou 1287 (administração direta ou indireta) |
   | Outros órgãos e entidades públicas | demais naturezas do grupo 1 |
   | Empresa | naturezas do grupo 2 |
   | Entidade sem fins lucrativos | naturezas do grupo 3 |
   | Organização internacional | naturezas do grupo 5 |
   | Agente financeiro intermediário | lista explícita por CNPJ (Banco do Brasil, Caixa e outros bancos pagadores), versionada |

   O significado oficial dos prefixos `RB`, `TN` e `PF` e dos códigos `-1`, `-2`, `-8`,
   `-11` e `-14` ainda será confirmado com a CGU. Até lá, a regra usa o formato observado,
   e a nota no portal diz "classificação do portal".
2. **Os valores nunca somem.** Lançamentos agregados, fluxos dentro da União, intermediários
   e sigilosos entram nos totais da lente B, num quadro próprio ("pagamentos agregados ou
   intermediados"). Ficam fora só dos rankings de destinatários.
3. **A identidade do favorecido é o par código + nome.** Para PJ, o CNPJ basta; o nome
   segue o cadastro mais recente, e os nomes históricos ficam guardados. Para PF, a chave é
   o código mascarado **mais** o nome, exatamente como na fonte. Nunca se juntam nomes
   diferentes com o mesmo código, nem códigos diferentes com o mesmo nome.
4. **Pessoas físicas são publicadas (D3):** nome e CPF mascarado como a CGU publica, nos
   mapas agregados, nas tabelas e nos rankings.
5. **Salvaguardas** (LGPD art. 7º, §§ 3º, 6º e 7º; CLAUDE.md §23.2):
   1. **Finalidade:** transparência e controle social do gasto público, a mesma que
      justificou a publicação pela CGU (LRF art. 48-A).
   2. **Fidelidade à fonte:** o portal nunca desmascara, deduz ou completa CPF. Não cruza a
      pessoa física com outras bases para identificá-la (endereço, outros cadastros) e não
      acrescenta atributos pessoais que a CGU não publica.
   3. **Homônimos:** toda ficha e ranking de PF traz o aviso de que o CPF mascarado não
      distingue pessoas e pode haver homônimos, com link para a página oficial na CGU.
   4. **Atualização:** se a CGU corrigir ou retirar um registro, o próximo release segue a
      fonte. Os releases antigos não ficam navegáveis no portal.
   5. **Canal do titular:** pedidos de correção vão para `portal@opendatabrasil.org`. A
      resposta segue a fonte oficial: correções de conteúdo são encaminhadas à CGU.
   6. **`noindex` nas fichas de PF (D3.1, aprovada em 2026-11-22):** as fichas
      individuais de pessoa física não são indexadas por buscadores (`noindex` no HTML e
      no cabeçalho `X-Robots-Tag`), mas continuam acessíveis no portal. Reduz a exposição
      sem esconder o dado.
6. **Sigiloso** (`-11`) aparece como "valor sigiloso na fonte", com o total. O portal nunca
   tenta inferir quem é.
7. **Benefícios sociais** (Bolsa Família, BPC e outros, com NIS) ficam fora desta fase.
   Quando entrarem, terão ADR próprio.
