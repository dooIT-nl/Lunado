# d1_framecalculator

Vervangt de handmatige serveractie "Framecalculator" op de verkooporder door
een nette module met configureerbare instellingen.

## Functionaliteit

* Knop **Framecalculator** op de verkooporder (naast *Voorbeeld*, verborgen
  bij geannuleerde orders). Opent de externe framecalculator in het huidige
  venster met `orderid` (order-id) en `customerid` (klant-id) als
  parameters — identiek aan de oude serveractie.
* **Instellingen** onder Verkoop → Configuratie → Instellingen → kopje
  **Framecalculator**:
  * *Framecalculator URL* — basis-URL zonder parameters;
  * *Framecalculator API Key* — de **platte** (niet URL-encoded) sleutel;
    encoding gebeurt automatisch bij het opbouwen van de URL. Het veld wordt
    als wachtwoord weergegeven.
* Zonder configuratie geeft de knop een duidelijke foutmelding met de
  vindplaats van de instellingen.

## Migratie (post_init_hook)

Bij installatie op een database met de oude handmatige serveractie:

1. URL en API-key worden uit de actiecode geparsed en — alleen als de
   instellingen nog leeg zijn — overgenomen (de key wordt gedecodeerd, want
   die stond URL-encoded in de actie).
2. Knop-verwijzingen naar de oude actie worden uit nog actieve Studio-views
   geknipt.
3. De oude serveractie wordt verwijderd.

Op een verse database doet de hook niets; de instellingen zijn dan leeg.

## Beveiliging

De API-key staat **niet** in de code of repo, alleen als systeemparameter in
de database (richtlijn: geen credentials in code). Controleer na de
productie-deploy éénmalig of de overgenomen key klopt.

## Contact

dooIT B.V. — https://dooit.nl
