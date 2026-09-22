"""Symlet scaling filters $h^{(N)}_k$ (least-asymmetric Daubechies) -- numberdb.org/T395.

For each 2 <= N <= 20 and 0 <= k <= 2N - 1, this generator computes the
low-pass reconstruction filter coefficient h_k of the least-asymmetric
Daubechies wavelet symN, normalised so that sum_k h_k = sqrt(2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The coefficients are algebraic. The generator builds the exact spectral factor
in QQbar from the Daubechies polynomial P_N(y), uses the root choices that
identify PyWavelets' symN coefficient rows, and converts the exact algebraic
coefficients to real balls for storage. Before writing it checks the
normalisation, vanishing moments, quadrature-mirror orthogonality, and the
source rows in PyWavelets.
"""

import os
import re
import sys
from functools import lru_cache
from math import comb

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.qqbar import QQbar, _init_qqbar
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


_init_qqbar()

TABLE = os.environ.get("NUMBERDB_TABLE", "T395")
MIN_N = 2
MAX_N = 20
DIGITS = 100
WORKING_GUARD = 128
CHECK_DIGITS = 160
CHECK_GUARD = 256
ZERO = QQbar(0)
ONE = QQbar(1)
TWO = QQbar(2)

ROOT_CHOICES = {
    2: "0",
    3: "00",
    4: "011",
    5: "1100",
    6: "10011",
    7: "110000",
    8: "0110011",
    9: "00111100",
    10: "100110011",
    11: "0011110000",
    12: "10011001100",
    13: "000011111100",
    14: "0001111001100",
    15: "00001111110000",
    16: "100001111001100",
    17: "0011111100000011",
    18: "10011110000110011",
    19: "000011001111110000",
    20: "1001100001111001100",
}

PYWAVELETS_REFERENCE = {
    2: (
        "0.48296291314469025", "0.83651630373746899", "0.22414386804185735",
        "-0.12940952255092145",
    ),
    3: (
        "0.33267055295095688", "0.80689150931333875", "0.45987750211933132",
        "-0.13501102001039084", "-0.085441273882241486", "0.035226291882100656",
    ),
    4: (
        "0.032223100604042702", "-0.012603967262037833", "-0.099219543576847216",
        "0.29785779560527736", "0.80373875180591614", "0.49761866763201545",
        "-0.02963552764599851", "-0.075765714789273325",
    ),
    5: (
        "0.019538882735286728", "-0.021101834024758855", "-0.17532808990845047",
        "0.016602105764522319", "0.63397896345821192", "0.72340769040242059",
        "0.1993975339773936", "-0.039134249302383094", "0.029519490925774643",
        "0.027333068345077982",
    ),
    6: (
        "-0.007800708325034148", "0.0017677118642428036", "0.044724901770665779",
        "-0.021060292512300564", "-0.072637522786462516", "0.3379294217276218",
        "0.787641141030194", "0.49105594192674662", "-0.048311742585632998",
        "-0.11799011114819057", "0.0034907120842174702", "0.015404109327027373",
    ),
    7: (
        "0.010268176708511255", "0.0040102448715336634", "-0.10780823770381774",
        "-0.14004724044296152", "0.28862963175151463", "0.76776431700316405",
        "0.5361019170917628", "0.017441255086855827", "-0.049552834937127255",
        "0.067892693501372697", "0.03051551316596357", "-0.01263630340325193",
        "-0.0010473848886829163", "0.0026818145682578781",
    ),
    8: (
        "0.0018899503327594609", "-0.0003029205147213668", "-0.014952258337048231",
        "0.0038087520138906151", "0.049137179673607506", "-0.027219029917056003",
        "-0.051945838107709037", "0.3644418948353314", "0.77718575170052351",
        "0.48135965125837221", "-0.061273359067658524", "-0.14329423835080971",
        "0.0076074873249176054", "0.031695087811492981", "-0.00054213233179114812",
        "-0.0033824159510061256",
    ),
    9: (
        "0.0010694900329086053", "-0.00047315449868008311", "-0.010264064027633142",
        "0.0088592674934004842", "0.06207778930288603", "-0.018233770779395985",
        "-0.19155083129728512", "0.035272488035271894", "0.61733844914093583",
        "0.717897082764412", "0.238760914607303", "-0.054568958430834071",
        "0.00058346274612580684", "0.03022487885827568", "-0.01152821020767923",
        "-0.013271967781817119", "0.00061978088898558676", "0.0014009155259146807",
    ),
    10: (
        "-0.00045932942100465878", "5.7036083618494284e-005", "0.0045931735853118284",
        "-0.00080435893201654491", "-0.02035493981231129", "0.0057649120335819086",
        "0.049994972077376687", "-0.0319900568824278", "-0.035536740473817552",
        "0.38382676106708546", "0.7695100370211071", "0.47169066693843925",
        "-0.070880535783243853", "-0.15949427888491757", "0.011609893903711381",
        "0.045927239231092203", "-0.0014653825813050513", "-0.0086412992770224222",
        "9.5632670722894754e-005", "0.00077015980911449011",
    ),
    11: (
        "0.00048926361026192387", "0.00011053509764272153", "-0.0063896036664548919",
        "-0.0020034719001093887", "0.043000190681552281", "0.035266759564466552",
        "-0.14460234370531561", "-0.2046547944958006", "0.23768990904924897",
        "0.73034354908839572", "0.57202297801008706", "0.097198394458909473",
        "-0.022832651022562687", "0.069976799610734136", "0.0370374159788594",
        "-0.024080841595864003", "-0.0098579348287897942", "0.0065124956747714497",
        "0.00058835273539699145", "-0.0017343662672978692", "-3.8795655736158566e-005",
        "0.00017172195069934854",
    ),
    12: (
        "-0.00017906658697508691", "-1.8158078862617515e-005", "0.0023502976141834648",
        "0.00030764779631059454", "-0.014589836449234145", "-0.0026043910313322326",
        "0.057804179445505657", "0.01530174062247884", "-0.17037069723886492",
        "-0.07833262231634322", "0.46274103121927235", "0.76347909778365719",
        "0.39888597239022", "-0.022162306170337816", "-0.035848830736954392",
        "0.049179318299660837", "0.0075537806116804775", "-0.024220722675013445",
        "-0.0014089092443297553", "0.007414965517654251", "0.00018021409008538188",
        "-0.0013497557555715387", "-1.1353928041541452e-005", "0.00011196719424656033",
    ),
    13: (
        "7.0429866906944016e-005", "3.6905373423196241e-005", "-0.0007213643851362283",
        "0.00041326119884196064", "0.0056748537601224395", "-0.0014924472742598532",
        "-0.020749686325515677", "0.017618296880653084", "0.092926030899137119",
        "0.0088197576704205465", "-0.14049009311363403", "0.11023022302137217",
        "0.64456438390118564", "0.69573915056149638", "0.19770481877117801",
        "-0.12436246075153011", "-0.059750627717943698", "0.013862497435849205",
        "-0.017211642726299048", "-0.02021676813338983", "0.0052963597387250252",
        "0.0075262253899680996", "-0.00017094285853022211", "-0.0011360634389281183",
        "-3.5738623648689009e-005", "6.8203252630753188e-005",
    ),
    14: (
        "4.4618977991475265e-005", "1.9329016965523917e-005",
        "-0.00060576018246643346", "-7.3214213567023991e-005", "0.0045326774719456481",
        "0.0010131419871842082", "-0.019439314263626713", "-0.0023650488367403851",
        "0.069827616361807551", "0.025898587531046669", "-0.15999741114652205",
        "-0.058111823317717831", "0.47533576263420663", "0.75997624196109093",
        "0.39320152196208885", "-0.035318112114979733", "-0.057634498351326995",
        "0.037433088362853452", "0.0042805204990193782", "-0.029196217764038187",
        "-0.0027537747912240711", "0.010037693717672269", "0.00036647657366011829",
        "-0.002579441725933078", "-6.2865424814776362e-005", "0.00039843567297594335",
        "1.1210865808890361e-005", "-2.5879090265397886e-005",
    ),
    15: (
        "2.8660708525318081e-005", "2.1717890150778919e-005",
        "-0.00040216853760293483", "-0.00010815440168545525", "0.003481028737064895",
        "0.0015261382781819983", "-0.017171252781638731", "-0.0087447888864779517",
        "0.067969829044879179", "0.068393310060480245", "-0.13405629845625389",
        "-0.1966263587662373", "0.2439627054321663", "0.72184302963618119",
        "0.57864041521503451", "0.11153369514261872", "-0.04108266663538248",
        "0.040735479696810677", "0.021937642719753955", "-0.038876716876833493",
        "-0.019405011430934468", "0.010079977087905669", "0.003423450736351241",
        "-0.0035901654473726417", "-0.00026731644647180568", "0.0010705672194623959",
        "5.5122547855586653e-005", "-0.00016066186637495343",
        "-7.3596667989194696e-006", "9.7124197379633478e-006",
    ),
    16: (
        "-1.0797982104319795e-005", "-5.3964831793152419e-006",
        "0.00016545679579108483", "3.656592483348223e-005", "-0.0013387206066921965",
        "-0.00022211647621176323", "0.0069377611308027096", "0.001359844742484172",
        "-0.024952758046290123", "-0.0035102750683740089", "0.078037852903419913",
        "0.03072113906330156", "-0.15959219218520598", "-0.054040601387606135",
        "0.47534280601152273", "0.75652498787569711", "0.39712293362064416",
        "-0.034574228416972504", "-0.066983049070217779", "0.032333091610663785",
        "0.0048692744049046071", "-0.031051202843553064", "-0.0031265171722710075",
        "0.012666731659857348", "0.00071821197883178923", "-0.0038809122526038786",
        "-0.0001084456223089688", "0.00085235471080470952", "2.8078582128442894e-005",
        "-0.00010943147929529757", "-3.1135564076219692e-006",
        "6.2300067012207606e-006",
    ),
    17: (
        "3.7912531943321266e-006", "-2.4527163425832999e-006",
        "-7.6071244056051285e-005", "2.5207933140828779e-005", "0.0007198270642148971",
        "5.8400428694052584e-005", "-0.0039323252797979023", "-0.0019054076898526659",
        "0.012396988366648726", "0.0099529825235095976", "-0.01803889724191924",
        "-0.0072616347509287674", "0.016158808725919346", "-0.086070874720733381",
        "-0.15507600534974825", "0.18053958458111286", "0.68148899534492502",
        "0.65071662920454565", "0.14239835041467819", "-0.11856693261143636",
        "0.0172711782105185", "0.10475461484223211", "0.017903952214341119",
        "-0.033291383492359328", "-0.0048192128031761478", "0.010482366933031529",
        "0.0008567700701915741", "-0.0027416759756816018", "-0.00013864230268045499",
        "0.0004759963802638669", "-1.3506383399901165e-005",
        "-6.2937025975541919e-005", "2.7801266938414138e-006",
        "4.297343327345983e-006",
    ),
    18: (
        "-1.5131530692371587e-006", "7.8472980558317646e-007",
        "2.9557437620930811e-005", "-9.858816030140058e-006",
        "-0.00026583011024241041", "4.7416145183736671e-005", "0.0014280863270832796",
        "-0.00018877623940755607", "-0.0052397896830266083", "0.0010877847895956929",
        "0.015012356344250213", "-0.0032607442000749834", "-0.031712684731814537",
        "0.0062779445543116943", "0.028529597039037808", "-0.073799207290607169",
        "-0.032480573290138676", "0.40148386057061813", "0.75362914010179283",
        "0.47396905989393956", "-0.052029158983952786", "-0.15993814866932407",
        "0.033995667103947358", "0.084219929970386548", "-0.0050770851607570529",
        "-0.030325091089369604", "0.0016429863972782159", "0.0095021643909623654",
        "-0.00041152110923597756", "-0.0023138718145060992", "7.0212734590362685e-005",
        "0.00039616840638254753", "-1.4020992577726755e-005",
        "-4.5246757874949856e-005", "1.354915761832114e-006",
        "2.6126125564836423e-006",
    ),
    19: (
        "1.7509367995348687e-006", "2.0623170632395688e-006",
        "-2.8151138661550245e-005", "-1.6821387029373716e-005",
        "0.00027621877685734072", "0.00012930767650701415", "-0.0017049602611649971",
        "-0.00061792232779831076", "0.0082622369555282547", "0.0043193518748949689",
        "-0.027709896931311252", "-0.016908234861345205", "0.084072676279245043",
        "0.093630843415897141", "-0.11624173010739675", "-0.17659686625203097",
        "0.25826616923728363", "0.71955552571639425", "0.57814494533860505",
        "0.10902582508127781", "-0.067525058040294086", "0.0089545911730436242",
        "0.0070155738571741596", "-0.046635983534938946", "-0.022651993378245951",
        "0.015797439295674631", "0.0079684383206133063", "-0.005122205002583014",
        "-0.0011607032572062486", "0.0021214250281823303", "0.00015915804768084938",
        "-0.00063576451500433403", "-4.6120396002105868e-005", "0.0001155392333357879",
        "8.8733121737292863e-006", "-1.1880518269823984e-005",
        "-6.4636513033459633e-007", "5.4877327682158382e-007",
    ),
    20: (
        "-6.3291290447763946e-007", "-3.2567026420174407e-007",
        "1.22872527779612e-005", "4.5254222091516362e-006", "-0.00011739133516291466",
        "-2.6615550335516086e-005", "0.00074761085978205719", "0.00012544091723067259",
        "-0.0034716478028440734", "-0.0006111263857992088", "0.012157040948785737",
        "0.0019385970672402002", "-0.035373336756604236", "-0.0068437019650692274",
        "0.088919668028199561", "0.036250951653933078", "-0.16057829841525254",
        "-0.051088342921067398", "0.47199147510148703", "0.75116272842273002",
        "0.40583144434845059", "-0.029819368880333728", "-0.078994344928398158",
        "0.025579349509413946", "0.0081232283560096815", "-0.031629437144957966",
        "-0.0033138573836233591", "0.017004049023390339", "0.0014230873594621453",
        "-0.0066065857990888609", "-0.0003052628317957281", "0.0020889947081901982",
        "7.2159911880740349e-005", "-0.00049473109156726548",
        "-1.928412300645204e-005", "7.992967835772481e-005", "3.0256660627369661e-006",
        "-7.919361411976999e-006", "-1.9015675890554106e-007",
        "3.695537474835221e-007",
    ),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _complex_field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _decimal_to_qq(text):
    sign = -1 if text.startswith("-") else 1
    text = text.lstrip("+-")
    if "e" in text.lower():
        mantissa, exponent = re.split("[eE]", text)
        value = _decimal_to_qq(mantissa)
        exponent = int(exponent)
        if exponent >= 0:
            return sign * abs(value) * QQ(10) ** exponent
        return sign * abs(value) / (QQ(10) ** (-exponent))
    if "." not in text:
        return QQ(sign * int(text))
    whole, fractional = text.split(".", 1)
    numerator = int((whole or "0") + fractional)
    denominator = 10 ** len(fractional)
    return QQ(sign * numerator) / QQ(denominator)


@lru_cache(maxsize=None)
def pywavelets_reference_row(n):
    return tuple(_decimal_to_qq(value) for value in PYWAVELETS_REFERENCE[int(n)])


def _daubechies_polynomial(n):
    ring = PolynomialRing(QQ, "y")
    y = ring.gen()
    total = ring(0)
    for j in range(n):
        total += QQ(comb(n - 1 + j, j)) * y**j
    return total


def _reciprocal_pair(y_root):
    a = TWO - QQbar(4) * y_root
    discriminant = a * a - QQbar(4)
    square_root = discriminant.sqrt()
    return ((a + square_root) / TWO, (a - square_root) / TWO)


@lru_cache(maxsize=None)
def exact_filter_row(n):
    n = int(n)
    if n not in ROOT_CHOICES:
        raise ValueError("N must satisfy %d <= N <= %d" % (MIN_N, MAX_N))

    roots = tuple(_daubechies_polynomial(n).roots(QQbar, multiplicities=False))
    choices = ROOT_CHOICES[n]
    if len(roots) != len(choices):
        raise ArithmeticError("N=%d has %d roots but %d choices" % (
            n, len(roots), len(choices)))

    ring = PolynomialRing(QQbar, "z")
    z = ring.gen()
    polynomial = (1 + z) ** n
    for y_root, choice in zip(roots, choices):
        polynomial *= z - ring(_reciprocal_pair(y_root)[int(choice)])

    polynomial *= TWO.sqrt() / polynomial(ONE)
    row = tuple(polynomial.list())
    if len(row) != 2 * n:
        raise ArithmeticError("N=%d produced %d coefficients" % (n, len(row)))
    return row


def _as_real_ball(value, digits):
    ball = _complex_field(digits)(value)
    if not ball.imag().contains_zero():
        raise ArithmeticError("coefficient has nonzero imaginary part: %s" % ball)
    return ball.real()


def filter_row(n, digits=DIGITS):
    return tuple(_as_real_ball(value, digits) for value in exact_filter_row(int(n)))


def _assert_contains_zero(label, value):
    if not value.contains_zero():
        raise ArithmeticError("%s does not contain zero: %s" % (label, value))
    field = value.parent()
    if field(value.rad()) > field(10) ** (-120):
        raise ArithmeticError("%s has too wide a zero enclosure: %s" % (label, value))


def _check_normalisation(n, row, field):
    total = sum(row, field(0))
    _assert_contains_zero("N=%d normalisation" % n, total - field(2).sqrt())


def _check_vanishing_moments(n, row):
    for moment in range(n):
        total = sum(
            ((-1) ** k) * (k ** moment) * row[k]
            for k in range(2 * n)
        )
        _assert_contains_zero("N=%d moment=%d" % (n, moment), total)


def _check_orthogonality(n, row, field):
    for shift in range(-(n - 1), n):
        total = field(0)
        for k in range(2 * n):
            other = k - 2 * shift
            if 0 <= other < 2 * n:
                total += row[k] * row[other]
        expected = field(1) if shift == 0 else field(0)
        if not (total - expected).contains_zero():
            raise ArithmeticError(
                "N=%d even autocorrelation shift %d is %s, not %s"
                % (n, shift, total, expected)
            )
        _assert_contains_zero(
            "N=%d even autocorrelation shift %d" % (n, shift), total - expected
        )


def _check_pywavelets_source_row(n):
    field = _complex_field(CHECK_DIGITS, CHECK_GUARD)
    limit = _real_field(CHECK_DIGITS, CHECK_GUARD)(QQ(1) / QQ(10) ** 9)
    for k, (got, want) in enumerate(zip(exact_filter_row(n), pywavelets_reference_row(n))):
        error = abs(field(got) - field(want))
        if error > limit:
            raise ArithmeticError(
                "N=%d k=%d differs from PyWavelets source by %s" % (n, k, error)
            )


def run_integrity_checks(min_n=MIN_N, max_n=MAX_N):
    field = _real_field(CHECK_DIGITS, CHECK_GUARD)
    for n in range(min_n, max_n + 1):
        exact_row = exact_filter_row(n)
        row = tuple(_as_real_ball(value, CHECK_DIGITS) for value in exact_row)
        _check_normalisation(n, row, field)
        _check_vanishing_moments(n, row)
        _check_orthogonality(n, row, field)
        _check_pywavelets_source_row(n)


class SymletScalingFilters(numberdb.Generator):

    table = TABLE
    parameters = ("N", "k")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for n in range(MIN_N, max_n + 1):
            for k in range(2 * n):
                yield {"N": str(n), "k": str(k)}

    def value(self, params, digits):
        n = int(params["N"])
        k = int(params["k"])
        return filter_row(n, digits)[k]


def fill_full_draft_once(generator, message):
    """Write the finished draft document and attach this generator."""
    import yaml
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, to_text

    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, generator.table, identity, value)
        written = to_text(value, wanted, generator.format)
        _check_precision(generator.table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "table.yaml"), encoding="utf8") as handle:
        document = yaml.load(handle, Loader=yaml.BaseLoader)
    document["Numbers"] = entries.as_list()

    client = numberdb.Client()
    headers = {
        "X-Produced-By": _producer(
            generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")
        ),
        "X-Edit-Message": message,
        "X-Run-Id": run,
        "X-Numberdb-Client": "numberdb-python/%s" % numberdb.__version__,
    }
    answer = client.submit(
        "/api/table/%s" % str(generator.table).lstrip("tT"),
        yaml.dump(document, sort_keys=False, allow_unicode=True),
        headers,
    )

    attached = []
    for name, body in sorted(_source_files(generator).items()):
        attach(
            generator.table,
            name,
            body,
            run=run,
            client=client,
            message=message,
            rigour=generator.rigour,
        )
        attached.append(name)
    answer["attached"] = attached
    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = SymletScalingFilters()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_full_draft_once(
            generator,
            message="Symlet scaling filter coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
