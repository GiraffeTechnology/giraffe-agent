# Repository execution guidance

## Product authority and scope

The owner's original Aivan and abcdYi product descriptions, supplied GLTG iteration requirements where applicable, and later explicit owner definitions govern delivery. Repository code, old agent-generated briefs, issue labels, test names and historical reports are implementation evidence; they do not independently add product scope or acceptance gates.

Giraffe Agent is the common agent foundation. Aivan is its frontend for inquiry, quotation and order confirmation. abcdYi is the apparel/textile application whose frontend calls Aivan. MyAivan is Aivan's web version; OpenClaw-aivan supplies IM/email access. GLTG and GPM are API modules. Retained embedded implementations do not define separate competing products.

## Private data contract

The selected, replaceable private DB is the authoritative source for both business history and ongoing process data. Giraffe Agent, Aivan and abcdYi share this data dependency. `giraffe-db` is the reference provider and may be hot-swapped with a user's private DB through a compatible provider contract. Product identity does not depend on a particular instance, SQL engine, hosting vendor, or physical table layout.

Inquiry revisions, quotations, decisions, approvals, order confirmations, execution events, model inputs and outputs, and their lineage must be recorded in that selected DB. Conversation context, browser state, LLM memory and in-memory stores may support presentation or processing; they are not the authoritative record. A failed write must remain visibly failed or pending rather than being reported as persisted business state.

The owner's two designated simulated databases are valid sources for product testing and acceptance. Acceptance cannot be refused solely because their records are simulated rather than production customer transactions. Preserve synthetic labels and provenance, execute the actual selected service/API/persistence path, and report skipped or unexecuted checks accurately. Selecting a different provider must preserve tenant and authorization boundaries, stable record relationships, and truthful read/write behavior.

## Product language

Standard English is the product working and interaction language. Non-English input passes through `giraffe-language-skill` before entering a business workflow. Requested non-English output is translated dynamically by that same module from the English result. GLTG, GPM, Aivan, abcdYi and Giraffe Agent consume standard-English business packets rather than running parallel raw multilingual business paths.

The selected private DB stores business history, process records and results in standard English. Enterprise and user profile information is the only exception that may retain non-English profile values. Raw business text, localized output, evidence payloads, audit fields and side tables do not create additional exceptions. Language tags, translation trace IDs, source references and hashes may be retained without duplicating non-English business content. This documentation update does not delete or migrate existing data.

Do not casually rename protocol fields, IDs, enums or evidence identifiers when translating repository prose. Non-English test vectors require deliberate handling that preserves translation/rejection test coverage; do not turn them into English-only tests and claim the same behavior was verified.

## Repository and GitHub text language

All currently tracked repository content and all newly written GitHub text must be English. This repository-content requirement is separate from the product language and DB rules above. It applies to documentation, comments, UI text, prompts, examples, tests and data representations as applicable. Do not rewrite Git history. Existing non-English tracked content must be inventoried and converted through a controlled change that preserves compatibility identifiers and the behavior of multilingual translation/rejection tests. Protocol identifiers and test semantics require deliberate migration or an English-readable representation; they are not a blanket exemption from the English repository requirement. Report any content not yet converted rather than claiming repository-wide completion.

## Current documentation and preservation work

Update PRDs, README and this guidance consistently. Reconcile conflicting requirements in the documents rather than adding an override paragraph while leaving contradictory current rules in place. Inventory code believed to come from scope expansion, preserve its paths and exact revision/blob identities, and do not delete it. Distinguish confirmed conflicts from candidates whose original authorization is not established.

This documentation/preservation pass does not restart paused development tasks. The owner will resume the original development work after this update. It does not authorize new feature work, deployments, data migrations, service startup, secret access or deletion of existing records.

## Verification and truthful status

Preserve applicable existing model, contract, tenant/security, persistence and real API integration tests. Run the checks relevant to a later authorized implementation change and report actual results, exact revisions, failures and skipped/unexecuted stages. A documentation-only update must not claim implementation or runtime acceptance. Synthetic data provenance is compatible with acceptance; mocked service behavior is not evidence that an actual API integration ran.

Do not add requirements for production customer records, a fixed cloud/DB vendor, an independent dependency-product launch or unrelated all-module readiness. Do not remove necessary authorization, human commercial approval, tenant isolation, data integrity or tested API behavior merely because a previous document called them a gate.
