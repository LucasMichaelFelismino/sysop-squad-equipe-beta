# ADR 001 — Separação de Arquivos de Mídia (Object Storage)

- **Status:** Aceito
- **Sprint:** 1

## Contexto

A projeção BOTE de 5 anos indica aproximadamente 35 TB de anexos fotográficos, muito acima do volume dos dados estruturados (~292 GB).

## Decisão

Os anexos serão armazenados em Object Storage em nuvem (ex.: AWS S3 ou tecnologia equivalente). O banco transacional/geoespacial manterá somente a chave/identificador persistente do objeto e seus metadados; URLs assinadas e temporárias serão geradas pela API quando necessário.

## Alternativas Rejeitadas

Armazenar imagens como BLOBs no banco transacional, pois mistura cargas com perfis distintos, aumenta o crescimento do banco e dificulta rotinas de backup, restauração e escalabilidade.

## Consequências

- **Positivo:** banco principal menor e separado da carga de arquivos.
- **Negativo:** necessidade de gerenciar autorização de acesso, ciclo de vida e integridade entre metadados e objetos.

## Governança

O API Gateway limitará uploads a no máximo 5 MB por arquivo; acesso a anexos será autorizado e, quando aplicável, realizado por URL assinada com expiração.
