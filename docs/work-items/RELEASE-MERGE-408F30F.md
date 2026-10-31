# Integrate teammate408f30f with accepted landing correction

Owner: release F; user directly requested merge and conflict resolution. Root/H review holds expanded rollout until runtime evidence. Base8833355, correctionc73c636, teammate408f30f. Preserve history and existing ZInD controls/guides. No new provider calls or key changes.

Paths: integration/release files and targeted fixes required by integrated validation. Main merge/push authorized; production cutover waits for qualification. Do not modify root checkout user .env.example. No subagents.

Acceptance: integrated gates; exact image built WITH_BLENDER=1; synthetic Studio workflow with real Blender on VM at1CPU/1GiB/pids128/worker timeout180s; canonical snapshot/catalog/media preserved; evidence strict JSON (unknown duration=null); no claim40-call cap is USD budget. Current healthy production975d91a retained.

Status: merge has no textual conflicts; landing correction and teammate history both retained. Candidate runtime qualification pending.

Candidatec6d9aa3 pushedmain includescorrectionc73c636 andteammate80f477b NumPyfix. No textualconflicts. Exactimagebd91d278… WITH_BLENDER=1 passed actualDebian3.4.1 Studio geometry→finalreview→publish under1CPU/1GiB/pids128, worker180s, noOOM, networknone/0providercalls, isolatedtmpfs. Gateall commandPASS; localcore2PASS1SKIP explicitlyrecorded. JSONreport unknown duration=null. Evidence deploy/evidence/integrated-c6d9aa3/.

BLOCKED rollout: anotherwriter replaced production975d91a with80f477b/image1123f156… duringF snapshot attempt; productionhealthy butmissinglandingcorrection. F didnotcutover andstoppedproductionmutations; rootasked toresolvelease. Snapshotpreflight interruptedbeforebackupcreation, notclaimedPASS. Expandedcandidate staysHOLD pendinglease/currentbaselinebackup/HTTPbrowservalidation.
