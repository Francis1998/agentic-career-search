# Changelog

All notable changes to **agentic-career-search** are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `RemotiveAdapter` (`source_type: remotive`): public Remotive careers boards (remotive.com). Postings are recognised by `/remote-jobs/{id}`, `/remote-job/{id}`, `/jobs/{id}`, `/job/{id}`, `/positions/{id}` URL shapes; board indexes, apply/login/signin/about/index steps, and navigation links are ignored. See ADR-156 and `docs/guides/REMOTIVE_SOURCE_GUIDE.md`.
- `WelcometothejungleAdapter` (`source_type: welcometothejungle`): public Welcome to the Jungle careers boards (welcometothejungle.com). Postings are recognised by `/jobs/{id}`, `/job/{id}`, `/companies/{slug}/jobs/{id}`, `/offers/{id}`, `/offer/{id}` URL shapes; board indexes, bare company pages, apply/login/signin/about/index steps, and navigation links are ignored. See ADR-155 and `docs/guides/WELCOMETOTHEJUNGLE_SOURCE_GUIDE.md`.
- `WeworkremotelyAdapter` (`source_type: weworkremotely`): public WeWorkRemotely careers boards (weworkremotely.com). Postings are recognised by `/remote-jobs/{id}`, `/jobs/{id}`, `/job/{id}`, `/listings/{id}`, `/listing/{id}` URL shapes; board indexes, apply/login/signin/about/index steps, and navigation links are ignored. See ADR-154 and `docs/guides/WEWORKREMOTELY_SOURCE_GUIDE.md`.
- `RemoteokAdapter` (`source_type: remoteok`): public RemoteOK careers boards (remoteok.com). Postings are recognised by `/remote-jobs/{id}`, `/remote-job/{id}`, `/jobs/{id}`, `/job/{id}` URL shapes; board indexes, apply/login/signin/about/index steps, and navigation links are ignored. See ADR-153 and `docs/guides/REMOTEOK_SOURCE_GUIDE.md`.

- `BuiltinAdapter` (`source_type: builtin`): public Built In careers boards (builtin.com / builtinnyc.com / builtinchicago.com). Postings are recognised by `/job/{id}`, `/jobs/{id}`, `/company-jobs/{id}`, `/careers/job/{id}`, `/role/{id}` URL shapes; board indexes, apply/login/signin/about steps, and navigation links are ignored. See ADR-152 and `docs/guides/BUILTIN_SOURCE_GUIDE.md`.

- `OttaAdapter` (`source_type: otta`): public Otta careers boards (otta.com). Postings are recognised by `/jobs/{id}`, `/job/{id}`, `/roles/{id}`, `/role/{id}`, `/openings/{id}` URL shapes; board indexes, apply/login/signin/about steps, and navigation links are ignored. See ADR-151 and `docs/guides/OTTA_SOURCE_GUIDE.md`.

- `WellfoundAdapter` (`source_type: wellfound`): public Wellfound careers boards (wellfound.com / angel.co). Postings are recognised by `/jobs/{id}`, `/job/{id}`, `/role/{id}`, `/roles/{id}`, `/startup-jobs/{id}` URL shapes; board indexes, apply/login/signin/about steps, and navigation links are ignored. See ADR-150 and `docs/guides/WELLFOUND_SOURCE_GUIDE.md`.

- `YelloAdapter` (`source_type: yello`): public Yello careers boards. Postings
  are recognised by `/jobs/{id}`, `/job/{id}`, `/position/{id}`,
  `/positions/{id}`, and `/opening/{id}` URL shapes; board indexes,
  apply/login/signin/about steps, and navigation links are ignored. See ADR-149
  and `docs/guides/YELLO_SOURCE_GUIDE.md`.

- `PaycomAdapter` (`source_type: paycom`): public Paycom careers boards.
  Postings are recognised by `/jobs/{id}`, `/job/{id}`, `/posting/{id}`,
  `/postings/{id}`, and `/opportunity/{id}` URL shapes; board indexes,
  apply/login/signin/about steps, and navigation links are ignored. See ADR-148
  and `docs/guides/PAYCOM_SOURCE_GUIDE.md`.

- `HireVueAdapter` (`source_type: hirevue`): public HireVue careers boards.
  Postings are recognised by `/jobs/{id}`, `/job/{id}`, `/careers/{id}`,
  `/careers/job/{id}`, and `/requisition/{id}` URL shapes; board indexes,
  apply/login/signin/about steps, and navigation links are ignored. See ADR-147
  and `docs/guides/HIREVUE_SOURCE_GUIDE.md`.

- `JibeAdapter` (`source_type: jibe`): public Jibe careers boards
  (`*.jibe.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/position/{id}`, `/positions/{id}`, and `/requisition/{id}` URL shapes;
  board indexes, apply/login/signin/about steps, and navigation links are
  ignored. See ADR-146 and `docs/guides/JIBE_SOURCE_GUIDE.md`.

- `RadancyAdapter` (`source_type: radancy`): public Radancy careers boards
  (`*.radancy.com`, `*.jobs.net`). Postings are recognised by `/jobs/{id}`,
  `/job/{id}`, `/search/job/{id}`, `/careers/{id}`, and `/careers/job/{id}`
  URL shapes; board indexes, apply/login/signin/about steps, and navigation
  links are ignored. See ADR-145 and `docs/guides/RADANCY_SOURCE_GUIDE.md`.

- `SilkRoadAdapter` (`source_type: silkroad`): public SilkRoad Recruiting boards
  (`*.silkroad.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/posting/{id}`, `/postings/{id}`, and `/opportunity/{id}` URL shapes;
  board indexes, apply/login/signin/about steps, and navigation links are
  ignored. See ADR-144 and `docs/guides/SILKROAD_SOURCE_GUIDE.md`.

- `AdpAdapter` (`source_type: adp`): public ADP Recruiting boards
  (`*.adp.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/requisitions/{id}` URL shapes;
  board indexes, apply/login/signin/about steps, and navigation links are
  ignored. See ADR-143 and `docs/guides/ADP_SOURCE_GUIDE.md`.

- `ParadoxAdapter` (`source_type: paradox`): public Paradox Olivia careers
  boards (`*.paradox.ai`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/opportunities/{id}` URL shapes;
  board indexes, apply/login/signin/about steps, and navigation links are
  ignored. See ADR-142 and `docs/guides/PARADOX_SOURCE_GUIDE.md`.

- `CatsoneAdapter` (`source_type: catsone`): public CATS careers boards
  (`*.catsone.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/postings/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-141 and `docs/guides/CATSONE_SOURCE_GUIDE.md`.
- `ApplicantProAdapter` (`source_type: applicantpro`): public ApplicantPro
  careers boards (`*.applicantpro.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/openings/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-140 and
  `docs/guides/APPLICANTPRO_SOURCE_GUIDE.md`.
- `BrassringAdapter` (`source_type: brassring`): public IBM Kenexa BrassRing
  careers boards (`*.brassring.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/jobdetail/{id}`, `/FgJobDetail/{id}`, and
  `/careers/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-139 and
  `docs/guides/BRASSRING_SOURCE_GUIDE.md`.
- `HireezAdapter` (`source_type: hireez`): public HireEZ / Hiretual careers
  boards (`*.hireez.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/positions/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-138 and
  `docs/guides/HIREEZ_SOURCE_GUIDE.md`.
- `EployAdapter` (`source_type: eploy`): public Eploy careers
  boards (`*.eploy.net`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/role/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-137 and
  `docs/guides/EPLOY_SOURCE_GUIDE.md`.
- `BeameryAdapter` (`source_type: beamery`): public Beamery careers
  boards (`*.beamery.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/campaign/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-136 and
  `docs/guides/BEAMERY_SOURCE_GUIDE.md`.
- `CornerstoneAdapter` (`source_type: cornerstone`): public Cornerstone OnDemand careers
  boards (`*.csod.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/opening/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-135 and
  `docs/guides/CORNERSTONE_SOURCE_GUIDE.md`.
- `PCRecruiterAdapter` (`source_type: pcrecruiter`): public PCRecruiter careers
  boards (`*.pcrecruiter.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/requisition/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-134 and
  `docs/guides/PCRECRUITER_SOURCE_GUIDE.md`.
- `JobDivaAdapter` (`source_type: jobdiva`): public JobDiva careers
  boards (`*.jobdiva.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/jd/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-133 and
  `docs/guides/JOBDIVA_SOURCE_GUIDE.md`.
- `CrelateAdapter` (`source_type: crelate`): public Crelate careers
  boards (`*.crelate.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/opportunity/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-132 and
  `docs/guides/CRELATE_SOURCE_GUIDE.md`.
- `TribepadAdapter` (`source_type: tribepad`): public Tribepad careers
  boards (`*.tribepad.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/vacancy/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-131 and
  `docs/guides/TRIBEPAD_SOURCE_GUIDE.md`.
- `VincereAdapter` (`source_type: vincere`): public Vincere careers
  boards (`*.vincere.io`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/job-detail/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-130 and
  `docs/guides/VINCERE_SOURCE_GUIDE.md`.
- `RecruitCrmAdapter` (`source_type: recruitcrm`): public RecruitCRM careers
  boards (`*.recruitcrm.io`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/opening/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-129 and
  `docs/guides/RECRUITCRM_SOURCE_GUIDE.md`.
- `CareerPlugAdapter` (`source_type: careerplug`): public CareerPlug careers
- `TrackerRmsAdapter` (`source_type: trackerrms`): public TrackerRMS careers
- `ApplicantStackAdapter` (`source_type: applicantstack`): public ApplicantStack
  careers boards (`*.applicantstack.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/{id}`, `/careers/job/{id}`, and
  `/postings/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-126 and
  `docs/guides/APPLICANTSTACK_SOURCE_GUIDE.md`.
- `TalentLyftAdapter` (`source_type: talentlyft`): public TalentLyft careers boards
  (`apply.talentlyft.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and
  `/openings/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-125 and
  `docs/guides/TALENTLYFT_SOURCE_GUIDE.md`.
- `PageUpAdapter` (`source_type: pageup`): public PageUp careers boards
  (`careers.pageuppeople.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and
  `/opportunities/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-123 and
  `docs/guides/PAGEUP_SOURCE_GUIDE.md`.
- `CeipalAdapter` (`source_type: ceipal`): public Ceipal careers boards
  (`jobs.ceipal.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and
  `/requisitions/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-124 and
  `docs/guides/CEIPAL_SOURCE_GUIDE.md`.
- `JobylonAdapter` (`source_type: jobylon`): public Jobylon careers boards
  (`jobs.jobylon.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, `/positions/{id}`, and
  `/vacancies/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-122 and
  `docs/guides/JOBYLON_SOURCE_GUIDE.md`.
- `JobAdderAdapter` (`source_type: jobadder`): public JobAdder careers boards
- `DoverAdapter` (`source_type: dover`): public Dover careers boards
- `PolymerAdapter` (`source_type: polymer`): public Polymer careers boards
- `LoxoAdapter` (`source_type: loxo`): public Loxo careers boards
- `HibobAdapter` (`source_type: hibob`): public HiBob (Bob) careers boards
  (`*.hibob.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/positions/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-118 and `docs/guides/HIBOB_SOURCE_GUIDE.md`.

- `PaylocityAdapter` (`source_type: paylocity`): public Paylocity careers boards
  (`*.paylocity.com`). Postings are recognised by `/jobs/{id}`, `/JobDetails/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/openings/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-116 and `docs/guides/PAYLOCITY_SOURCE_GUIDE.md`.
- `BullhornAdapter` (`source_type: bullhorn`): public Bullhorn careers boards
  (`*.bullhornstaffing.com`). Postings are recognised by `/jobs/{id}`, `/Job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/position/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-115 and `docs/guides/BULLHORN_SOURCE_GUIDE.md`.
- `UkgAdapter` (`source_type: ukg`): public UKG/UltiPro careers boards
  (`*.ultipro.com` / `*.ukg.net`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/opportunities/{id}`, `/opportunity/{id}`, and `/careers/job/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-114 and `docs/guides/UKG_SOURCE_GUIDE.md`.
- `FactorialAdapter` (`source_type: factorial`): public Factorial HR careers boards
  (`*.factorialhr.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/open-positions/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-113 and `docs/guides/FACTORIAL_SOURCE_GUIDE.md`.
- `ManatalAdapter` (`source_type: manatal`): public Manatal careers boards
  (`*.manatal.com`). Postings are recognised by `/jobs/{id}`, `/job/{id}`,
  `/careers/{id}`, `/careers/job/{id}`, and `/openings/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-110 and `docs/guides/MANATAL_SOURCE_GUIDE.md`.
- `JoinAdapter` (`source_type: join`): public Join careers boards (`join.com`).
  Postings are recognised by `/companies/{slug}/jobs/{id}`, `/jobs/{id}`,
  `/job/{id}`, and `/positions/{id}` URL shapes; board indexes, apply/login/signin/about
  steps, and navigation links are ignored. See ADR-112 and
  `docs/guides/JOIN_SOURCE_GUIDE.md`.
- `SoftgardenAdapter` (`source_type: softgarden`): public Softgarden careers boards
  (`*.softgarden.io`). Postings are recognised by `/job/{id}`, `/jobs/{id}`,
  `/vacancies/{id}`, `/vacancy/{id}`, and `/position/{id}` URL shapes; board
  indexes, apply/login/signin/about steps, and navigation links are ignored. See
  ADR-111 and `docs/guides/SOFTGARDEN_SOURCE_GUIDE.md`.
- `ClearCompanyAdapter` (`source_type: clearcompany`): public ClearCompany careers
  boards (`*.clearcompany.com`). Postings are recognised by `/careers/job/{id}`,
  `/careers/{id}`, `/jobs/{id}`, `/job/{id}-{slug}`, and `/position/{id}` URL
  shapes; board indexes, apply/login/signin/about steps, and navigation links are
  ignored. See ADR-107 and `docs/guides/CLEARCOMPANY_SOURCE_GUIDE.md`.
- `AppliedAdapter` (`source_type: applied`): public Applied careers boards
  (`*.applied.co`). Postings are recognised by `/jobs/{id}`, `/j/{id}`,
  `/role/{id}`, `/roles/{id}`, and `/job/{id}` URL shapes; board indexes,
  apply/login/signin/about steps, and navigation links are ignored. See ADR-108
  and `docs/guides/APPLIED_SOURCE_GUIDE.md`.- `HireologyAdapter` (`source_type: hireology`): public Hireology careers boards
- `RecruiterflowAdapter` (`source_type: recruiterflow`): public Recruiterflow
  careers boards (`*.recruiterflow.com`). Postings are recognised by
  `/jobs/{id}`, `/job/{id}`, `/careers/job/{id}`, `/openings/{id}`, and
  `/opening/{id}` URL shapes; board indexes, apply/login/signin/about steps,
  and navigation links are ignored. See ADR-109 and
  `docs/guides/RECRUITERFLOW_SOURCE_GUIDE.md`.
- `HireologyAdapter` (`source_type: hireology`): public Hireology careers boards
  (`careers.hireology.com`). Postings are recognised by `/jobs/{id}`,
  `/careers/job/{id}`, and `/job/{id}/{slug}` URL shapes; board indexes,
  apply/login/signin steps, and navigation links are ignored. See ADR-104 and
  `docs/guides/HIREOLOGY_SOURCE_GUIDE.md`.
- `DayforceAdapter` (`source_type: dayforce`): public Dayforce (Ceridian) careers
  boards (`*.dayforcehcm.com`). Postings are recognised by `/JobDetail/{id}`,
  `/careers/job/{id}`, `/MyCareer/JobDetail?jobId={id}`, and `/positions/{id}`
  URL shapes; board indexes, apply/login/signin steps, and navigation links are
  ignored. See ADR-105 and `docs/guides/DAYFORCE_SOURCE_GUIDE.md`.
- `HomerunAdapter` (`source_type: homerun`): public Homerun careers boards
  (`*.homerun.co`). Postings are recognised by `/jobs/{id}-{slug}`, `/o/{id}`,
  and `/vacancies/{id}` URL shapes; board indexes, apply/login/signin/about
  steps, and navigation links are ignored. See ADR-106 and
  `docs/guides/HOMERUN_SOURCE_GUIDE.md`.
- `JobScoreAdapter` (`source_type: jobscore`): public JobScore careers boards
  (`careers.jobscore.com` / `*.jobscore.com`). Postings are recognised by
  `/careers/{company}/jobs/{slug}-{id}`, `/careers/{company}/jobs/{id}`,
  `/jobs/{id}`, `/jobs/{slug}/{id}`, and `/position(s)/{id}` URL shapes;
  board indexes, apply/login/signin steps, and navigation links are ignored.
  See ADR-101 and `docs/guides/JOBSCORE_SOURCE_GUIDE.md`.
- `EightfoldAdapter` (`source_type: eightfold`): public Eightfold AI careers
  boards (`{company}.eightfold.ai`). Postings are recognised by
  `/careers/job/{id}`, `/careers/job/{id}/{slug}`, `/career_detail/{id}`,
  `/position/{id}`, and `/jobs/{id}` URL shapes; board indexes, apply/login
  steps, search facets, and navigation links are ignored. See ADR-102 and
  `docs/guides/EIGHTFOLD_SOURCE_GUIDE.md`.
- `AvatureAdapter` (`source_type: avature`): public Avature careers portals.
  Postings are recognised by `/JobDetail/{id}`, `/JobDetail.aspx?JobId={id}`,
  `/careers/{id}`, `/careers/job/{id}`, `/careers/VacancyDetail/{id}`,
  `/Vacancy/{id}`, and `/vacancies/{id}` URL shapes; board indexes,
  apply/login/RegisterCandidate/about links are ignored. See ADR-103 and
  `docs/guides/AVATURE_SOURCE_GUIDE.md`.
- `GemAdapter` (`source_type: gem`): public Gem careers boards
  (`jobs.gem.com` / `{company}.gem.com`). Postings are recognised by
  `/{company}/{jobId}`, `/jobs/{jobId}`, `/openings/{id}`, and
  `/careers/...` vanity URL shapes; board indexes, apply/login steps, and
  navigation links are ignored. See ADR-100 and
  `docs/guides/GEM_SOURCE_GUIDE.md`.
- `ComeetAdapter` (`source_type: comeet`): public Comeet careers boards
  (`www.comeet.co` / `www.comeet.com`). Postings are recognised by
  `/jobs/{company}/{companyId}/{jobSlug}/{jobId}` URL shapes; board indexes,
  apply/login steps, and navigation links are ignored. See ADR-098 and
  `docs/guides/COMEET_SOURCE_GUIDE.md`.
- `PhenomPeopleAdapter` (`source_type: phenom`): a dedicated adapter for public
  Phenom People careers sites. Postings are recognised by `/job/{id}/{slug}` or
  `/jobs/{id}` path shapes, while list/index/search/login/apply-step links are
  ignored. See ADR-095 and `docs/guides/PHENOM_SOURCE_GUIDE.md`.
- `RipplingAdapter` (`source_type: rippling`): public Rippling careers boards
  (`*.rippling.com`, especially `ats.rippling.com`). Postings are recognised by
  terminal `/jobs/{uuid}` detail paths; board indexes, application subpaths,
  generic navigation, and absolute non-Rippling links are ignored. See ADR-096
  and `docs/guides/RIPPLING_SOURCE_GUIDE.md`.
  ignored. See ADR-097 and `docs/guides/PHENOM_SOURCE_GUIDE.md`.
- `PinpointAdapter` (`source_type: pinpoint`): public Pinpoint HR careers boards
  (`{org}.pinpointhq.com`). Postings are recognised by `/postings/{uuid}`
  (optional locale prefix) or `/jobs/{jobId}` URL shapes; apply/login steps and
  board navigation links are ignored. See ADR-097 and
  `docs/guides/PINPOINT_SOURCE_GUIDE.md`.
- `FountainAdapter` (`source_type: fountain`): public Fountain careers boards
  (`{org}.fountain.com`, `web.fountain.com`). Postings are recognised by
  `/apply/{company}/{positionId}`, tenant `/apply/{slug}`, or `/jobs/{jobId}`,
  `/openings/{id}`, and `/positions/{id}` URL shapes; apply confirmation/login
  steps and board navigation links are ignored. See ADR-099 and
  `docs/guides/FOUNTAIN_SOURCE_GUIDE.md`.
- `ZohoRecruitAdapter` (`source_type: zoho_recruit`): a dedicated adapter for
  public Zoho Recruit (`*.zohorecruit.com`) careers portals and vanity-domain
  proxies. Postings are recognised by `jobId` / `jid` / `job_id` query ids or
  terminal `/job/{id}` / `/jobs/{id}` / `/careers/{id}` /
  `/Jobs/Careers/{id}` path shapes; apply/login steps and `source=apply` /
  `mode=apply` links are ignored. See ADR-093 and
  `docs/guides/ZOHO_RECRUIT_SOURCE_GUIDE.md`.
- `BreezyHrAdapter` (`source_type: breezyhr`): a dedicated adapter for public
  Breezy HR careers sites (`{company}.breezy.hr`). Postings are recognised
  by their terminal `/p/{positionId}` URL shape (optional hyphenated title
  slug). See ADR-091 and `docs/guides/BREEZYHR_SOURCE_GUIDE.md`.
- `FreshteamAdapter` (`source_type: freshteam`): public Freshteam careers boards. See ADR-094 and `docs/guides/FRESHTEAM_SOURCE_GUIDE.md`.
- `SuccessFactorsAdapter` (`source_type: successfactors`): a dedicated adapter
  for public SAP SuccessFactors (`*.successfactors.com` / `*.successfactors.eu`)
  careers portals. Postings are recognised by `jobId` / `career_job_req_id`
  query requisitions or terminal `/job/{id}` / `/jobs/{id}` path shapes;
  apply/login steps are ignored. See ADR-090 and
  `docs/guides/SUCCESSFACTORS_SOURCE_GUIDE.md`.
- `OracleTaleoAdapter` (`source_type: oracle_taleo`): a dedicated adapter for
  public Oracle Taleo (`*.taleo.net`) and Oracle Cloud HCM careers portals.
  Postings are recognised by `job=` / `jobId` query requisitions or terminal
  `/job/{id}` / `/jobs/{id}` path shapes; apply/login steps are ignored. See
  ADR-089 and `docs/guides/ORACLE_TALEO_SOURCE_GUIDE.md`.
- `WorkdayAdapter` (`source_type: workday`): a structured-JSON adapter for public
  Workday careers boards (`{tenant}.wd{N}.myworkdayjobs.com`). The listing page
  is a client-rendered SPA, so the adapter POSTs to the public CXS endpoint
  `/wday/cxs/{tenant}/{site}/jobs` (hard page size 20), maps each
  `jobPostings[]` entry onto `{origin}/{locale}/{site}{externalPath}`, and
  captures the trailing `JR…` / `R-…` requisition token as `external_id`. See
  ADR-088 and `docs/guides/WORKDAY_SOURCE_GUIDE.md`.
- `IcimsAdapter` (`source_type: icims`): a dedicated adapter for public iCIMS
  careers portals (`careers-{tenant}.icims.com`, plus vanity-domain proxies).
  Postings are recognised purely by their `/jobs/{jobId}/{slug}/job` URL shape
  (terminal literal `job`, numeric id, slug optional) — so the `/jobs/search`
  grid, the application step, and navigation links are ignored and the numeric
  id is captured as the `external_id`. Titles fall back to the anchor `title`
  attribute when the anchor text is empty. See ADR-087.
- `JobviteAdapter` (`source_type: jobvite`): a dedicated adapter for public
  Jobvite careers sites (`jobs.jobvite.com/{company}`). Postings are recognised
  purely by their terminal *singular* `/job/{jobId}` URL shape (also matched
  under a `/careers/{company}` prefix), where `jobId` is a mixed-case
  alphanumeric id — so the plural `/jobs` list page, the `/job/{jobId}/apply`
  step, and navigation links are ignored and the id is captured as the
  `external_id`. See ADR-086.

### Fixed
- `TeamtailorAdapter`: mixed-case / Title-Case optional title slugs in
  `/jobs/{jobId}-{Slug}` posting URLs are now accepted.

- `JobviteAdapter`: empty-text posting anchors that expose the role name on the
  `title` attribute are now kept (mirrors iCIMS `_anchor_title`), instead of
  being dropped because only visible anchor text was considered.
- `SmartRecruitersAdapter`: posting hrefs whose optional title slug uses
  mixed/Title Case (e.g. `744000123456789-Senior-Backend-Engineer`) are
  recognised again. The previous `_JOB_ID_PATTERN` required a strictly
  lowercase slug, so `_is_posting_href` silently dropped those openings.
- `JsonLdAdapter`: `jobLocationType` values expressed as IRIs
  (`https://schema.org/Telecommute`) or CURIEs (`schema:Telecommute`) now
  resolve to `location="Remote"` via the same `_type_term` local-term reduction
  already used for `@type`, instead of requiring the exact bare string
  `TELECOMMUTE`.
- `JsonLdAdapter`: a `Place.address` expressed as a (possibly single-element)
  JSON-LD array of `PostalAddress` objects now yields a location string instead
  of being silently dropped. `jobLocation` already handled a list of Places and
  `hiringOrganization` handled a list of orgs, but `_place_to_string` required
  `address` to be a string or dict — leaving `location=None` for otherwise
  complete postings.
- `JsonLdAdapter`: a `hiringOrganization` expressed as a (possibly
  single-element) JSON-LD array now yields its company name instead of being
  silently dropped. `jobLocation` already handled the array form, but
  `hiringOrganization` did not, so a wrapped organization name was lost and the
  company fell back to the host-derived token.
- `JsonLdAdapter`: `JobPosting` blocks whose `@type` is a fully-qualified IRI
  (`https://schema.org/JobPosting`) or a context-prefixed CURIE
  (`schema:JobPosting`) are now recognised. Only the bare `JobPosting` term was
  matched previously, silently dropping every posting emitted with an IRI/CURIE
  type. Type matching now compares the local term after the final `/` or `:`.
- `JsonLdAdapter`: distinct `JobPosting` blocks that omit their own `url` no
  longer collapse into a single candidate. Such postings previously all fell
  back to `base_url` and were discarded after the first by URL deduplication;
  dedup now keys explicit-url postings by URL and url-less postings by title.
- Bumped the `pillow` dev-dependency floor to `>=12.3.0` so the scheduled
  Security Scan (`pip-audit`) no longer fails on the five advisories
  (PYSEC-2026-2253..2257) affecting the previously resolved 12.2.0.

### Added
- `BambooHrAdapter` (`source_type: bamboohr`): the package's first structured-JSON
  source adapter, for public BambooHR hosted careers boards
  (`{tenant}.bamboohr.com`). BambooHR careers pages are client-rendered, so the
  adapter reads the tenant's public `/careers/list` JSON endpoint directly and
  maps each opening to `/careers/{id}`. Handles object and string locations plus
  the `isRemote` flag, and skips blank-id rows that would otherwise collapse
  distinct postings under URL dedup. See ADR-085.
- `PersonioAdapter` (`source_type: personio`): a dedicated adapter for public
  Personio careers sites (`{tenant}.jobs.personio.de` / `.com`), the dominant
  ATS across DACH/EU employers. Postings are recognised purely by their terminal
  *singular* `/job/{jobId}` URL shape (an optional hyphenated title slug may
  trail the id), so the plural `/jobs` list page, the `/job/{jobId}/apply`
  application step, and navigation links are ignored and the numeric posting id
  is captured as the `external_id`. See ADR-084.
- `TeamtailorAdapter` (`source_type: teamtailor`): a dedicated adapter for public
  Teamtailor careers sites (`{company}.teamtailor.com`). Postings are recognised
  purely by their terminal `/jobs/{jobId}-{slug}` URL shape (also matched under a
  custom-domain `/careers` prefix), so the jobs list page, application forms, and
  navigation links are ignored and the numeric posting id is captured as the
  `external_id`. See ADR-083.
- `SmartRecruitersAdapter` (`source_type: smartrecruiters`): a dedicated adapter
  for public SmartRecruiters careers sites (`jobs.smartrecruiters.com/{company}`).
  Postings are recognised purely by their `/{company}/{jobId}-{slug}` URL shape,
  so careers-site navigation and legal links are ignored and the numeric posting
  id is captured as the `external_id`. See ADR-082.
- `RecruiteeAdapter` (`source_type: recruitee`): a dedicated adapter for public
  Recruitee careers sites (`{company}.recruitee.com`). Postings are recognised
  purely by their `/o/{slug}` URL shape, so careers-site navigation and legal
  links are ignored and the posting slug is captured as the `external_id`.
  See ADR-081.
- `WorkableAdapter` (`source_type: workable`): a dedicated adapter for public
  Workable job boards (`apply.workable.com/{company}`). Postings are recognised
  purely by their `/{company}/j/{shortcode}` URL shape, so board navigation and
  legal links are ignored and the posting shortcode is captured as the
  `external_id`. See ADR-080.
- `AshbyAdapter` (`source_type: ashby`): a dedicated adapter for public Ashby
  job boards (`jobs.ashbyhq.com/{org}`). Postings are recognised purely by their
  `/{org}/{uuid}` URL shape, so board navigation and legal links are ignored and
  the posting UUID is captured as the `external_id`. See ADR-079.
- `JsonLdAdapter` (`source_type: jsonld`): a vendor-neutral source adapter that
  extracts `schema.org/JobPosting` structured data from embedded JSON-LD, so any
  board publishing Google-Jobs data (SmartRecruiters, Workable, custom career
  sites) is supported without a bespoke scraper. See ADR-078.

### Fixed
- Posting location resolution misread a `relocation` badge as the posting's
  location. The shared lookup selected any element whose `class` merely
  *contained* the substring `location` (`[class*=location]`), so a posting
  advertising relocation assistance surfaced that text as its location even when
  no real location element was present. Location is now resolved only from a
  `class` token that *is* `location` (optionally hyphen/underscore-delimited,
  e.g. `job-location`), via a shared `find_location_text` helper reused by the
  Ashby, Workable, Recruitee, SmartRecruiters, and Teamtailor adapters.
- `LeverAdapter` fallback anchor matching (used when the primary `div.posting`
  selector is absent, e.g. alternative or client-rendered board markup) searched
  for a `/jobs/` path segment that real Lever posting URLs
  (`jobs.lever.co/{company}/{uuid}`) never contain, so every posting was silently
  dropped. The fallback now recognises the true trailing-UUID posting shape while
  still accepting a whole `jobs` path segment used by some embedded board variants.
- `GreenhouseAdapter` fallback anchor matching accepted any href containing the
  bare substring `/job`, so careers navigation links such as `/job_alerts` or
  `/jobseekers/faq` surfaced as phantom job candidates on boards that omit
  `.opening` containers. Matching now requires a whole `jobs` path segment (or a
  `gh_jid` query parameter), keeping only genuine postings.
- `JsonLdAdapter` left the location unset for remote-only postings that expressed
  `jobLocationType` as a single-element list (`["TELECOMMUTE"]`) rather than the
  bare string. JSON-LD permits any property to be an array, so both forms are
  now recognised and resolve to `Remote`.
- LLM enrichment silently dropped summaries when an OpenAI-compatible gateway
  (LiteLLM, vLLM, OpenRouter) returned `choices[0].message.content` as a list of
  structured content parts (`[{"type": "text", "text": ...}]`) instead of a bare
  string. The normalizer now extracts and joins the `text` of each part.
- Greenhouse adapter collapsed word boundaries when a title or location
  contained nested inline markup (e.g. `Senior <span>Backend</span> Engineer`
  became `SeniorBackendEngineer`); text is now joined with a space, matching the
  Lever adapter.

## [v0.4.12] — 2025-09-12

### Added
- Extended crawler module with improved error handling
- Added structured logging for application operations
- New unit tests covering edge cases in workflow pipeline

### Changed
- Refactored retry logic to use exponential backoff with jitter
- Improved type annotations across core modules
- Updated dependency pins to latest stable versions

### Fixed
- Resolved race condition in async crawler handler
- Fixed incorrect application timeout calculation

## [v0.1.0] — 2025-08-22

### Added
- Initial project scaffold with job search automation core
- Basic autoapply_agent implementation
- README and setup documentation
