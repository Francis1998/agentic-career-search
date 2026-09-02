"""FastAPI application factory and lifecycle wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.adapters.adp import AdpAdapter
from autoapply_agent.adapters.aijobs import AijobsAdapter
from autoapply_agent.adapters.applicantpro import ApplicantProAdapter
from autoapply_agent.adapters.applicantstack import ApplicantStackAdapter
from autoapply_agent.adapters.applied import AppliedAdapter
from autoapply_agent.adapters.arcdev import ArcdevAdapter
from autoapply_agent.adapters.ashby import AshbyAdapter
from autoapply_agent.adapters.authenticjobs import AuthenticjobsAdapter
from autoapply_agent.adapters.avature import AvatureAdapter
from autoapply_agent.adapters.bamboohr import BambooHrAdapter
from autoapply_agent.adapters.beamery import BeameryAdapter
from autoapply_agent.adapters.brassring import BrassringAdapter
from autoapply_agent.adapters.breezyhr import BreezyHrAdapter
from autoapply_agent.adapters.builtin import BuiltinAdapter
from autoapply_agent.adapters.bullhorn import BullhornAdapter
from autoapply_agent.adapters.careerplug import CareerPlugAdapter
from autoapply_agent.adapters.catsone import CatsoneAdapter
from autoapply_agent.adapters.ceipal import CeipalAdapter
from autoapply_agent.adapters.clearcompany import ClearCompanyAdapter
from autoapply_agent.adapters.comeet import ComeetAdapter
from autoapply_agent.adapters.cornerstone import CornerstoneAdapter
from autoapply_agent.adapters.crelate import CrelateAdapter
from autoapply_agent.adapters.cryptojobs import CryptojobsAdapter
from autoapply_agent.adapters.dayforce import DayforceAdapter
from autoapply_agent.adapters.dice import DiceAdapter
from autoapply_agent.adapters.dover import DoverAdapter
from autoapply_agent.adapters.dynamitejobs import DynamitejobsAdapter
from autoapply_agent.adapters.eightfold import EightfoldAdapter
from autoapply_agent.adapters.eploy import EployAdapter
from autoapply_agent.adapters.eurotechjobs import EurotechjobsAdapter
from autoapply_agent.adapters.factorial import FactorialAdapter
from autoapply_agent.adapters.flexjobs import FlexjobsAdapter
from autoapply_agent.adapters.fountain import FountainAdapter
from autoapply_agent.adapters.fourdayweek import FourdayweekAdapter
from autoapply_agent.adapters.freshteam import FreshteamAdapter
from autoapply_agent.adapters.gem import GemAdapter
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.adapters.hibob import HibobAdapter
from autoapply_agent.adapters.himalayas import HimalayasAdapter
from autoapply_agent.adapters.hireez import HireezAdapter
from autoapply_agent.adapters.hireology import HireologyAdapter
from autoapply_agent.adapters.hirevue import HireVueAdapter
from autoapply_agent.adapters.homerun import HomerunAdapter
from autoapply_agent.adapters.icims import IcimsAdapter
from autoapply_agent.adapters.jazzhr import JazzHrAdapter
from autoapply_agent.adapters.jibe import JibeAdapter
from autoapply_agent.adapters.jobadder import JobAdderAdapter
from autoapply_agent.adapters.jobdiva import JobDivaAdapter
from autoapply_agent.adapters.jobgether import JobgetherAdapter
from autoapply_agent.adapters.jobscore import JobScoreAdapter
from autoapply_agent.adapters.jobspresso import JobspressoAdapter
from autoapply_agent.adapters.jobvite import JobviteAdapter
from autoapply_agent.adapters.jobylon import JobylonAdapter
from autoapply_agent.adapters.join import JoinAdapter
from autoapply_agent.adapters.jooble import JoobleAdapter
from autoapply_agent.adapters.jsonld import JsonLdAdapter
from autoapply_agent.adapters.justremote import JustremoteAdapter
from autoapply_agent.adapters.levelsfyi import LevelsfyiAdapter
from autoapply_agent.adapters.lever import LeverAdapter
from autoapply_agent.adapters.loxo import LoxoAdapter
from autoapply_agent.adapters.manatal import ManatalAdapter
from autoapply_agent.adapters.nodesk import NodeskAdapter
from autoapply_agent.adapters.nofluffjobs import NofluffjobsAdapter
from autoapply_agent.adapters.oracle_taleo import OracleTaleoAdapter
from autoapply_agent.adapters.otta import OttaAdapter
from autoapply_agent.adapters.pageup import PageUpAdapter
from autoapply_agent.adapters.pangian import PangianAdapter
from autoapply_agent.adapters.paradox import ParadoxAdapter
from autoapply_agent.adapters.paycom import PaycomAdapter
from autoapply_agent.adapters.paylocity import PaylocityAdapter
from autoapply_agent.adapters.pcrecruiter import PCRecruiterAdapter
from autoapply_agent.adapters.personio import PersonioAdapter
from autoapply_agent.adapters.phenom import PhenomPeopleAdapter
from autoapply_agent.adapters.pinpoint import PinpointAdapter
from autoapply_agent.adapters.polymer import PolymerAdapter
from autoapply_agent.adapters.powertofly import PowertoflyAdapter
from autoapply_agent.adapters.pythonjobs import PythonjobsAdapter
from autoapply_agent.adapters.radancy import RadancyAdapter
from autoapply_agent.adapters.recruitcrm import RecruitCrmAdapter
from autoapply_agent.adapters.recruitee import RecruiteeAdapter
from autoapply_agent.adapters.recruiterflow import RecruiterflowAdapter
from autoapply_agent.adapters.remoteco import RemotecoAdapter
from autoapply_agent.adapters.remoteleaf import RemoteleafAdapter
from autoapply_agent.adapters.remoteok import RemoteokAdapter
from autoapply_agent.adapters.remotive import RemotiveAdapter
from autoapply_agent.adapters.rippling import RipplingAdapter
from autoapply_agent.adapters.silkroad import SilkRoadAdapter
from autoapply_agent.adapters.simplyhired import SimplyhiredAdapter
from autoapply_agent.adapters.smartrecruiters import SmartRecruitersAdapter
from autoapply_agent.adapters.softgarden import SoftgardenAdapter
from autoapply_agent.adapters.successfactors import SuccessFactorsAdapter
from autoapply_agent.adapters.talentlyft import TalentLyftAdapter
from autoapply_agent.adapters.teamtailor import TeamtailorAdapter
from autoapply_agent.adapters.trackerrms import TrackerRmsAdapter
from autoapply_agent.adapters.tribepad import TribepadAdapter
from autoapply_agent.adapters.ukg import UkgAdapter
from autoapply_agent.adapters.vincere import VincereAdapter
from autoapply_agent.adapters.welcometothejungle import WelcometothejungleAdapter
from autoapply_agent.adapters.wellfound import WellfoundAdapter
from autoapply_agent.adapters.weworkremotely import WeworkremotelyAdapter
from autoapply_agent.adapters.workable import WorkableAdapter
from autoapply_agent.adapters.workatastartup import WorkatastartupAdapter
from autoapply_agent.adapters.workday import WorkdayAdapter
from autoapply_agent.adapters.workingnomads import WorkingnomadsAdapter
from autoapply_agent.adapters.workintheopen import WorkintheopenAdapter
from autoapply_agent.adapters.yello import YelloAdapter
from autoapply_agent.adapters.ziprecruiter import ZiprecruiterAdapter
from autoapply_agent.adapters.zoho_recruit import ZohoRecruitAdapter
from autoapply_agent.api.routes_health import router as health_router
from autoapply_agent.api.routes_jobs import router as jobs_router
from autoapply_agent.api.routes_runs import router as runs_router
from autoapply_agent.api.routes_source_configs import router as source_configs_router
from autoapply_agent.core.config import Settings
from autoapply_agent.core.config import settings as default_settings
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import SourceType
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.services.llm_enrichment import LLMEnrichmentService
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService
from autoapply_agent.services.worker import InProcessWorker


def _create_api_router() -> APIRouter:
    """Create aggregate API router.

    Returns:
        Configured API router.
    """

    router = APIRouter()
    router.include_router(health_router)
    router.include_router(source_configs_router)
    router.include_router(runs_router)
    router.include_router(jobs_router)
    return router


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application instance.

    Args:
        custom_settings: Optional settings override for tests.

    Returns:
        FastAPI app instance.
    """

    active_settings = custom_settings or default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        engine = create_engine(active_settings.database_url)
        session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)

        app.state.settings = active_settings
        app.state.engine = engine
        app.state.session_factory = session_factory

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        llm_enrichment_service = (
            LLMEnrichmentService(active_settings) if active_settings.llm_enable_enrichment else None
        )
        worker = InProcessWorker(
            session_factory=session_factory,
            adapters={
                SourceType.ADP: AdpAdapter(active_settings.http_user_agent),
                SourceType.AIJOBS: AijobsAdapter(active_settings.http_user_agent),
                SourceType.APPLICANTPRO: ApplicantProAdapter(active_settings.http_user_agent),
                SourceType.APPLICANTSTACK: ApplicantStackAdapter(active_settings.http_user_agent),
                SourceType.APPLIED: AppliedAdapter(active_settings.http_user_agent),
                SourceType.ARCDEV: ArcdevAdapter(active_settings.http_user_agent),
                SourceType.ASHBY: AshbyAdapter(active_settings.http_user_agent),
                SourceType.AVATURE: AvatureAdapter(active_settings.http_user_agent),
                SourceType.BAMBOOHR: BambooHrAdapter(active_settings.http_user_agent),
                SourceType.BEAMERY: BeameryAdapter(active_settings.http_user_agent),
                SourceType.BRASSRING: BrassringAdapter(active_settings.http_user_agent),
                SourceType.BREEZYHR: BreezyHrAdapter(active_settings.http_user_agent),
                SourceType.BUILTIN: BuiltinAdapter(active_settings.http_user_agent),
                SourceType.BULLHORN: BullhornAdapter(active_settings.http_user_agent),
                SourceType.CAREERPLUG: CareerPlugAdapter(active_settings.http_user_agent),
                SourceType.CATSONE: CatsoneAdapter(active_settings.http_user_agent),
                SourceType.CEIPAL: CeipalAdapter(active_settings.http_user_agent),
                SourceType.CLEARCOMPANY: ClearCompanyAdapter(active_settings.http_user_agent),
                SourceType.COMEET: ComeetAdapter(active_settings.http_user_agent),
                SourceType.CORNERSTONE: CornerstoneAdapter(active_settings.http_user_agent),
                SourceType.CRELATE: CrelateAdapter(active_settings.http_user_agent),
                SourceType.DAYFORCE: DayforceAdapter(active_settings.http_user_agent),
                SourceType.DOVER: DoverAdapter(active_settings.http_user_agent),
                SourceType.DYNAMITEJOBS: DynamitejobsAdapter(active_settings.http_user_agent),
                SourceType.EIGHTFOLD: EightfoldAdapter(active_settings.http_user_agent),
                SourceType.EPLOY: EployAdapter(active_settings.http_user_agent),
                SourceType.FACTORIAL: FactorialAdapter(active_settings.http_user_agent),
                SourceType.FLEXJOBS: FlexjobsAdapter(active_settings.http_user_agent),
                SourceType.FOUNTAIN: FountainAdapter(active_settings.http_user_agent),
                SourceType.FRESHTEAM: FreshteamAdapter(active_settings.http_user_agent),
                SourceType.GEM: GemAdapter(active_settings.http_user_agent),
                SourceType.GREENHOUSE: GreenhouseAdapter(active_settings.http_user_agent),
                SourceType.HIBOB: HibobAdapter(active_settings.http_user_agent),
                SourceType.HIMALAYAS: HimalayasAdapter(active_settings.http_user_agent),
                SourceType.HIREEZ: HireezAdapter(active_settings.http_user_agent),
                SourceType.HIREOLOGY: HireologyAdapter(active_settings.http_user_agent),
                SourceType.HIREVUE: HireVueAdapter(active_settings.http_user_agent),
                SourceType.HOMERUN: HomerunAdapter(active_settings.http_user_agent),
                SourceType.ICIMS: IcimsAdapter(active_settings.http_user_agent),
                SourceType.JAZZHR: JazzHrAdapter(active_settings.http_user_agent),
                SourceType.JIBE: JibeAdapter(active_settings.http_user_agent),
                SourceType.JOBADDER: JobAdderAdapter(active_settings.http_user_agent),
                SourceType.JOBDIVA: JobDivaAdapter(active_settings.http_user_agent),
                SourceType.JOBSCORE: JobScoreAdapter(active_settings.http_user_agent),
                SourceType.JOBVITE: JobviteAdapter(active_settings.http_user_agent),
                SourceType.JOBYLON: JobylonAdapter(active_settings.http_user_agent),
                SourceType.JOBSPRESSO: JobspressoAdapter(active_settings.http_user_agent),
                SourceType.JOIN: JoinAdapter(active_settings.http_user_agent),
                SourceType.JUSTREMOTE: JustremoteAdapter(active_settings.http_user_agent),
                SourceType.JSONLD: JsonLdAdapter(active_settings.http_user_agent),
                SourceType.LEVER: LeverAdapter(active_settings.http_user_agent),
                SourceType.LOXO: LoxoAdapter(active_settings.http_user_agent),
                SourceType.MANATAL: ManatalAdapter(active_settings.http_user_agent),
                SourceType.NODESK: NodeskAdapter(active_settings.http_user_agent),
                SourceType.ORACLE_TALEO: OracleTaleoAdapter(active_settings.http_user_agent),
                SourceType.OTTA: OttaAdapter(active_settings.http_user_agent),
                SourceType.PAGEUP: PageUpAdapter(active_settings.http_user_agent),
                SourceType.PANGIAN: PangianAdapter(active_settings.http_user_agent),
                SourceType.PARADOX: ParadoxAdapter(active_settings.http_user_agent),
                SourceType.PAYCOM: PaycomAdapter(active_settings.http_user_agent),
                SourceType.PAYLOCITY: PaylocityAdapter(active_settings.http_user_agent),
                SourceType.PCRECRUITER: PCRecruiterAdapter(active_settings.http_user_agent),
                SourceType.PERSONIO: PersonioAdapter(active_settings.http_user_agent),
                SourceType.PHENOM: PhenomPeopleAdapter(active_settings.http_user_agent),
                SourceType.PINPOINT: PinpointAdapter(active_settings.http_user_agent),
                SourceType.POLYMER: PolymerAdapter(active_settings.http_user_agent),
                SourceType.POWERTOFLY: PowertoflyAdapter(active_settings.http_user_agent),
                SourceType.NOFLUFFJOBS: NofluffjobsAdapter(active_settings.http_user_agent),
                SourceType.CRYPTOJOBS: CryptojobsAdapter(active_settings.http_user_agent),
                SourceType.WORKATASTARTUP: WorkatastartupAdapter(active_settings.http_user_agent),
                SourceType.LEVELSFYI: LevelsfyiAdapter(active_settings.http_user_agent),
                SourceType.WORKINTHEOPEN: WorkintheopenAdapter(active_settings.http_user_agent),
                SourceType.DICE: DiceAdapter(active_settings.http_user_agent),
                SourceType.PYTHONJOBS: PythonjobsAdapter(active_settings.http_user_agent),
                SourceType.JOOBLE: JoobleAdapter(active_settings.http_user_agent),
                SourceType.SIMPLYHIRED: SimplyhiredAdapter(active_settings.http_user_agent),
                SourceType.ZIPRECRUITER: ZiprecruiterAdapter(active_settings.http_user_agent),
                SourceType.RADANCY: RadancyAdapter(active_settings.http_user_agent),
                SourceType.RECRUITCRM: RecruitCrmAdapter(active_settings.http_user_agent),
                SourceType.RECRUITEE: RecruiteeAdapter(active_settings.http_user_agent),
                SourceType.RECRUITERFLOW: RecruiterflowAdapter(active_settings.http_user_agent),
                SourceType.REMOTECO: RemotecoAdapter(active_settings.http_user_agent),
                SourceType.REMOTELEAF: RemoteleafAdapter(active_settings.http_user_agent),
                SourceType.FOURDAYWEEK: FourdayweekAdapter(active_settings.http_user_agent),
                SourceType.REMOTEOK: RemoteokAdapter(active_settings.http_user_agent),
                SourceType.REMOTIVE: RemotiveAdapter(active_settings.http_user_agent),
                SourceType.RIPPLING: RipplingAdapter(active_settings.http_user_agent),
                SourceType.SILKROAD: SilkRoadAdapter(active_settings.http_user_agent),
                SourceType.SMARTRECRUITERS: SmartRecruitersAdapter(active_settings.http_user_agent),
                SourceType.SOFTGARDEN: SoftgardenAdapter(active_settings.http_user_agent),
                SourceType.SUCCESSFACTORS: SuccessFactorsAdapter(active_settings.http_user_agent),
                SourceType.TALENTLYFT: TalentLyftAdapter(active_settings.http_user_agent),
                SourceType.TEAMTAILOR: TeamtailorAdapter(active_settings.http_user_agent),
                SourceType.TRACKERRMS: TrackerRmsAdapter(active_settings.http_user_agent),
                SourceType.TRIBEPAD: TribepadAdapter(active_settings.http_user_agent),
                SourceType.UKG: UkgAdapter(active_settings.http_user_agent),
                SourceType.VINCERE: VincereAdapter(active_settings.http_user_agent),
                SourceType.WELCOMETOTHEJUNGLE: WelcometothejungleAdapter(
                    active_settings.http_user_agent
                ),
                SourceType.WELLFOUND: WellfoundAdapter(active_settings.http_user_agent),
                SourceType.WEWORKREMOTELY: WeworkremotelyAdapter(active_settings.http_user_agent),
                SourceType.WORKINGNOMADS: WorkingnomadsAdapter(active_settings.http_user_agent),
                SourceType.WORKABLE: WorkableAdapter(active_settings.http_user_agent),
                SourceType.WORKDAY: WorkdayAdapter(active_settings.http_user_agent),
                SourceType.YELLO: YelloAdapter(active_settings.http_user_agent),
                SourceType.ZOHO_RECRUIT: ZohoRecruitAdapter(active_settings.http_user_agent),
                SourceType.AUTHENTICJOBS: AuthenticjobsAdapter(active_settings.http_user_agent),
                SourceType.EUROTECHJOBS: EurotechjobsAdapter(active_settings.http_user_agent),
                SourceType.JOBGETHER: JobgetherAdapter(active_settings.http_user_agent),
            },
            scoring_service=DeterministicScoringService(),
            planning_service=DeterministicPlanningService(),
            llm_enrichment_service=llm_enrichment_service,
            poll_interval_seconds=active_settings.worker_poll_interval_seconds,
            default_timeout_seconds=active_settings.http_timeout_seconds,
            max_jobs_per_source=active_settings.max_jobs_per_source,
        )
        app.state.worker = worker

        if active_settings.enable_worker:
            await worker.start()

        try:
            yield
        finally:
            await worker.stop()
            await engine.dispose()

    app = FastAPI(title=active_settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(_create_api_router())
    return app


app = create_app()
