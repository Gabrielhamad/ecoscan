# Education and collection audit

Reviewed: 2026-09-20.

## Scope and evidence

The Aprender view covers the six supported recognition classes. Education does
not imply that the current model reliably identifies all examples. Cooking oil
and medicines remain manual guidance, not automatic detection.

Sources used:

- PET recovery and applications: https://abipet.org.br/revalorizacao/
- Aluminium energy comparison (sector source, not app impact): https://abal.org.br/noticia/abal-assina-protocolo-para-elaboracao-de-plano-de-descarbonizacao-com-o-ministerio-do-meio-ambiente/
- Paper fibre cycles: https://iba.org/sustentabilidade/economia-circular/
- Glass recovery: https://abividro.org.br/sustentabilidade/
- Battery reverse logistics: https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/pilhas-e-baterias/
- Electronics reverse logistics: https://sinir.gov.br/perfis/logistica-reversa/logistica-reversa/eletroeletronicos/
- Ipea 2010 study of economic/environmental recycling benefits: https://repositorio.ipea.gov.br/bitstreams/51fe3ce8-2ad2-4313-b05f-16b4648abbe2/download

The Ipea study is historical research, not an evaluation of EcoScan. Sector
associations provide process information, not independent evidence of app impact.
No tonnes, avoided emissions or income are inferred from uploaded photographs.
Evaluate learning with before/after questions; assess operational quality using
review completion and corrected predictions. Measure actual recycling only with
partner receipt/mass records, consent, and a stated comparison methodology.

## Collection locations

The embedded list is intentionally partial: six operating Ecopontos in Sao Paulo
city verified against https://prefeitura.sp.gov.br/web/se/w/ecopontos/subse .
General Flores is excluded because the source reports temporary closure.
Old Glicerio and Armenia addresses were replaced. Ribeirao Preto entries were
removed from the active list. The entire city remains searchable via
https://coleta.prefeitura.sp.gov.br/ .

Only ordinary dry recyclable categories are marked accepted. Battery/electronic
acceptance is not inferred. Coordinates are unavailable, so internal results
must not be described as a nearest-point ranking. Verify operating conditions
with the operator before travel; this static audit needs periodic renewal.

## Accounts and verification

Supabase Auth showed a confirmed account and a completed sign-in during the
read-only check. Registration is not evidence that a photo report was submitted.
The new admin directory revalidates the token and admin role server-side, masks
email addresses, and consults Auth rather than local demonstration profiles.
Its live administrative UI still requires an authorized analyst login.

The Portuguese confirmation template is templates/confirm_signup_pt.html;
preserve the provider's ConfirmationURL token. Preparing this file does not
publish it: applying the subject/body in Supabase is a separate cloud action.
