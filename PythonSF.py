import chess
import chess.engine
import chess.pgn
import hashlib
from chess.engine import Cp

# from chess.engine import Cp, Mate, MateGiven
# import chess.syzygy

# filename = "result"
mpv = 4
VALUE_MATE = 32000
FILENAME: str = "test"
LONGTIME: int = 8
SHORTTIME: int = 2

#FILENAME: str= "mega2015_above2400"
PGNPATH = "pgndir"
ENGINENAME = "/usr/games/stockfish"
#PGNPATH = "D:/Dropbox/programming/realchess/Realchess QT/pgndir/"
#ENGINENAME = "D:/home/chess/engines/stockfish_14.1_win_x64/stockfish_14.1.exe"
TBPATH = "C:/Chess/tablebases/syzygy/3-4-5;C:/Chess/tablebases/syzygy/6DTZ;C:/Chess/tablebases/syzygy/6WDL"
SCOREFACTOR = 2  # voor stockfish 14 +120 = +1.2, in stockfish 12 was dit +240
simple_engine: chess.engine


class RC:
    def __init__(self):
        self.problemset = ""
        self.player_white = ""
        self.player_black = ""
        self.gamedate = ""
        self.hashval = 0
        self.nmoves = 0
        self.pgnstring = ""  # e4;e5;Nf3;f5;Bc4;fxe4;Nxe5;Qg5;d4;Qxg2;Qh5+
        self.fenfrom = ""
        self.fento = ""
        self.badengine_pvar = ""

        self.nblindmoves = 0
        self.pblindmoves = []
        self.blindmoves = []

        self.npv = {}  # nmoves
        self.score = {}  # nmoves, npv
        self.pvar = {}  # nmoves, npv
        self.var = {}  # nmoves, npv

    #  fill rc object
    def fillrc(self, game):
        self.problemset = FILENAME
        self.player_white = game.headers['White']
        self.player_black = game.headers['Black']
        self.gamedate = game.headers['Date']

    def clean(self):
        self.npv.clear()
        self.score.clear()
        self.pvar.clear()
        self.var.clear()


def format_pvinfo(pv, board: chess.Board):
    pvar = []
    var = []
    newboard = board.copy()
    for move in pv:
        var.append(move.uci())
        sanmove = newboard.san(move)
        pvar.append(sanmove)
        newboard.push(move)
    return pvar, var


# voor iedere pv maak movelist van uci info 
def format_moves(info):
    pv = []
    if 'pv' in info:
        pv = info['pv']
    return [move.uci() for move in pv]


def format_info(info):
    povscore = info["score"]  # povscore
    # score = info["score"].relative
    if povscore.is_mate():
        score = povscore.relative.score(mate_score=VALUE_MATE)

    else:
        score = povscore.relative.score()

    # Split up the score into a mate score and a centipawn score
    mate_score = povscore.relative.mate()
    centipawn_score = povscore.relative.score()

    moves = format_moves(info)

    output = {'mate_score': mate_score, 'cp_score': centipawn_score, 'score': score, "pv": moves}
    return output


def print_moves_to_file(rc: RC, filename):
    #    mpv = infos.size()
    resfile = open(filename, "a")  # append mode
    for key, value in rc.npv.items():
        resfile.write("npv%s: %s\n" % (key, value))
    for (x, y), v in rc.var.items():
        var = " ".join([i.strip() for i in rc.var[(x, y)]])
        resfile.write("var%s_%s:%s\n" % (x, y, var))
    for (x, y), v in rc.pvar.items():
        pvar = " ".join([i.strip() for i in rc.pvar[(x, y)]])
        #        resfile.write("pvar%s_%s: %s\n" % (x, y, rc.pvar[(x, y)]))
        resfile.write("pvar%s_%s:%s\n" % (x, y, pvar))
    for (x, y), v in rc.score.items():
        resfile.write("score%s_%s:%s\n" % (x, y, SCOREFACTOR * rc.score[(x, y)]))
    resfile.write("nmoves:%d\n" % len(rc.npv.items()))
    resfile.write("end\n\n")
    resfile.close()


def print_small_info_to_file(rc: RC, filename):
    resfile = open(filename, "a")  # append mode
    resfile.write("white:" + rc.player_white + "\n")
    resfile.write("black:" + rc.player_black + "\n")
    resfile.write("fento:" + rc.fento + "\n")
    resfile.write("pblindmoves:%s\n" % " ".join([i.strip() for i in rc.pblindmoves]))
    resfile.write("pvar 0:%s\n" % (rc.pvar[(1, 0)]))
    resfile.write("pvar 1:%s\n" % (rc.pvar[(1, 1)]))
    resfile.write("pvar bad engine:%s\n\n" % (rc.badengine_pvar))
    resfile.close()


def print_info_to_file(rc: RC, filename):
    #  resultname = "../results/rc_" + FILENAME + ".txt"
    resfile = open(filename, "a")  # append mode
    resfile.write("start\n")
    resfile.write("problemset:" + rc.problemset + "\n")
    resfile.write("white:" + rc.player_white + "\n")
    resfile.write("black:" + rc.player_black + "\n")
    resfile.write("gamedate:" + rc.gamedate + "\n")
    resfile.write("hash: %s\n" % rc.hashval)
    #  resfile.write("nmoves %d\n" % rc.nmoves)
    resfile.write("pgnstring:" + rc.pgnstring + "\n")
    resfile.write("fenfrom:" + rc.fenfrom + "\n")
    resfile.write("fento:" + rc.fento + "\n")
    resfile.write("nblindmoves:%d\n" % rc.nblindmoves)
    resfile.write("pblindmoves:%s\n" % " ".join([i.strip() for i in rc.pblindmoves]))
    resfile.write("blindmoves:%s\n" % " ".join([i.strip() for i in rc.blindmoves]))
    resfile.close()
    print_moves_to_file(rc, filename)


def analyse_cm_position(board: chess.Board, chessmove, chessengine: chess.engine, rcobject: RC):

    for limit in [SHORTTIME, LONGTIME]:

        # engine score
        search_limit = chess.engine.Limit(time=limit)
        infos_engine = chessengine.analyse(board, search_limit, multipv=1)
        #  best_move = infos_engine[0]['pv'][0]
        output_engine = [format_info(info) for info in infos_engine]
        score_engine = output_engine[0]['score']

        # analyseer de gespeelde zet
        pmove = board.san_and_push(chessmove)  # gespeelde zet
        infos = chessengine.analyse(board, search_limit, multipv=1)
        output = [format_info(info) for info in infos]
        score_gm = -output[0]['score']
        board.pop()

        wdl = Cp(score_engine).wdl(ply=board.ply()).expectation() - Cp(score_gm).wdl(ply=board.ply()).expectation()
        print("ChooseMove ", score_engine, " ", score_gm)
        if wdl < 0.1:
            return False, rcobject

    # gespeelde gm zet
    board.san_and_push(chessmove)  # voer de gm zet uit
    pvar, var = format_pvinfo(infos[0]['pv'], board)
    pvar.insert(0, pmove)
    rcobject.pvar[1, 1] = pvar
    var.insert(0, chessmove.uci())
    rcobject.var[1, 1] = var
    rcobject.score[1, 1] = output[0]['score']
    rcobject.nmoves = 1
    rcobject.npv[0] = 2

    # engine zet
    board.pop()
    pvar_engine, var_engine = format_pvinfo(infos_engine[0]['pv'], board)
    rcobject.pvar[1, 0] = pvar_engine
    rcobject.var[1, 0] = var_engine
    rcobject.score[1, 0] = output_engine[0]['score']
    #  last_pmove = board.san_and_push(chessmove)  # bord weer terug in oorspronkelijk state

    print("--> Found ChooseMove ", score_engine, " ", score_gm)
    print("GM: ", pvar)
    print("Engine: ", pvar_engine, "\n")
    return True, rcobject


def analyse_position(board: chess.Board, chessengine: chess.engine, rcobject: RC, nextmove, movenum: int):
    # maxblindmoves = 24
    global simple_engine

    # kort analyseren
    search_limit = chess.engine.Limit(time=SHORTTIME)
    infos = chessengine.analyse(board, search_limit, multipv=mpv)
    output = [format_info(info) for info in infos]

    if len(output) > 1:

        score0 = output[0]['score']
        score1 = output[1]['score']
        print("Analyse Position Short Time RC scores: ", score0, " ", score1)

        wdl = Cp(score0).wdl(ply=board.ply()).expectation() - Cp(score1).wdl(ply=board.ply()).expectation()
        if wdl < 0.1:
            return False

        # langer analyseren
        search_limit = chess.engine.Limit(time=LONGTIME)
        infos = chessengine.analyse(board, search_limit, multipv=mpv)
        output = [format_info(info) for info in infos]
        score0 = output[0]['score']
        score1 = output[1]['score']
        print("Analyse Position Long Time RC scores: ", score0, " ", score1)
        wdl = Cp(score0).wdl(ply=board.ply()).expectation() - Cp(score1).wdl(ply=board.ply()).expectation()
        if wdl < 0.1:
            return False

        infos_6ply = simple_engine.analyse(board, chess.engine.Limit(depth=6), multipv=2)
        output_6ply = [format_info(info) for info in infos_6ply]
        rcobject.badengine_pvar = output_6ply[0]['pv']
        print("Output simple engine:", output_6ply)
        print("Output :", output)
        print("Moves: simple engine:", output_6ply[0]['pv'][0], " normal engine:", output[0]['pv'][0], " player: ", nextmove)

        # als opgave EN NIET door tegenspeler gespeeld is, EN NIET door simpele engine gevonden is -> geen opgave
        if output[0]['pv'][0] == nextmove.uci():
            if output_6ply[0]['pv'][0] == output[0]['pv'][0]:  # and output_6ply[1]['pv'][1] is output[1]['pv'][1]:
                print("geen opgave: simpel ")
                return False

        # check voor terugslaan (wanneer er maar 1 mogelijkheid is voor terugslaan)
        # als je dit wilt gebruiken, zet dan stack=True bij copieren van board in main()
        """ 
        lastmove = board.pop()
        slaan = board.is_capture(lastmove)
        board.push(lastmove)
        print("lastmove ", lastmove.uci(), " slaan ", slaan, " square ", lastmove.to_square)

        if slaan and lastmove.to_square == infos[0]['pv'][0].to_square:  # sla op hetzelfde veld

            attackers = board.attackers(board.turn, lastmove.to_square)
            print(attackers)
            if len(board.attackers(board.turn, lastmove.to_square)) == 1:  # maar 1 attacker van het veld
                print("attacker ", board.attacks(lastmove.to_square))
                return False
        """
        npv = 0
        for info in infos:
            pvar, var = format_pvinfo(info['pv'], board)
            rcobject.pvar[movenum, npv] = pvar
            rcobject.var[movenum, npv] = var
            rcobject.score[movenum, npv] = output[npv]['score']
            npv += 1
            print("zet movenum ", movenum, " npv ", npv, "pvar: ", pvar)
        rcobject.npv[movenum] = npv

        #  doe de beste (eerste) zet
        board.push(infos[0]['pv'][0])
        movenum += 1
        print("beste zet ", infos[0]['pv'][0], "\n")

        # vind npv beste tegenzetten
        infos = chessengine.analyse(board, search_limit, multipv=mpv)
        output = [format_info(info) for info in infos]
        npv = 0
        for info in infos:
            pvar, var = format_pvinfo(info['pv'], board)
            rcobject.pvar[movenum, npv] = pvar
            rcobject.var[movenum, npv] = var
            rcobject.score[movenum, npv] = output[npv]['score']
            print("tegenzet movenum ", movenum, " npv: ", npv, "pvar: ", pvar)
            npv += 1
        rcobject.npv[movenum] = npv

        # doe de beste tegenzet
        board.push(infos[0]['pv'][0])

        return True
    else:
        return False


def main():
    global simple_engine
    # global maxblindmoves

    # 1. variables
    maxblindmoves = 24
    simple_engine = chess.engine.SimpleEngine.popen_uci(ENGINENAME)
    myengine = chess.engine.SimpleEngine.popen_uci(ENGINENAME)
    myengine.configure({"SyzygyPath": TBPATH})

    # 2. read pgn, pgn to game
    pgn = open(PGNPATH + FILENAME + ".pgn")

    while True:
        game = chess.pgn.read_game(pgn)
        if not game:
            return
        board = game.board()
        rcobject = RC()
        rcobject.fillrc(game)

        # 3. make pgnstring
        movelist = list(game.mainline_moves())
        board.reset()
        pgnstr = ""
        for move in game.mainline_moves():
            # print(move)
            pgnstr += board.san(move)
            pgnstr += ";"
            board.push(move)
            rcobject.pgnstring = pgnstr
        """
        with open("../results/hash.txt", 'r+') as f:
            oldhash = f.read()
        hashval = hashlib.sha1(pgnstr.encode('utf-8')).hexdigest()
        if oldhash == hashval:
            continue
        else:
            with open("../results/hash.txt", 'w+') as f:
                rcobject.hashval = hashval
                f.seek(0)
                f.write(hashval)
                f.truncate()
                f.close()
        """
        board.reset()
        fens = [board.fen()]
        board.reset()
        # counter = 0
        pmovestrings = []  # e4, Pc3
        movestrings = []  # e2e4,

        for move in game.mainline_moves():

            rcobject.clean()
            found_rc_problem = False

            m = move.uci()  # blindmovestring
            movestrings.append(m)
            sanmove = board.san(move)
            pmovestrings.append(sanmove)

            nmoves = len(pmovestrings)
            board.push(move)

            print("\n*********** NEW MOVE ******* ")
            print(nmoves, ": uci move ", m)

            fen = board.fen()
            print(nmoves, " ", fen)
            fens.append(fen)

            # write info to rcobject
            if nmoves < maxblindmoves:
                nblindmoves = nmoves
            else:
                nblindmoves = maxblindmoves
            rcobject.nmoves = nmoves
            rcobject.nblindmoves = nblindmoves
            rcobject.fenfrom = fens[nmoves - nblindmoves]
            rcobject.fento = fens[nmoves]

            print("movestring ", movestrings)

            if nmoves > 10:

                movenum = 1
                rcobject.pblindmoves = pmovestrings[nmoves - nblindmoves: nmoves]  # t/m nmoves
                rcobject.blindmoves = movestrings[nmoves - nblindmoves: nmoves]  # t/m nmoves

                # ChooseMove opgaven
                if len(movelist) > nmoves:
                    newboard = board.copy()
                    nextmove = movelist[nmoves]
                    found_cm_problem, rcobject = analyse_cm_position(newboard, nextmove, myengine, rcobject)
                    if found_cm_problem:
                        print_info_to_file(rcobject, "../results/cm_" + FILENAME + ".txt")

                # Realchess opgaven
                go_on = True
                rcobject.clean()
                newboard = board.copy(stack=False)
                while go_on and movenum < 10 and len(movelist) > nmoves:

                    nextmove = movelist[nmoves]
                    go_on = analyse_position(newboard, myengine, rcobject, nextmove, movenum)

                    # write important data to file
                    if go_on and movenum == 1:
                        found_rc_problem = True
                        print_small_info_to_file(rcobject, "../results/rc_small_" + FILENAME + ".txt")

                    movenum = movenum + 2

                if found_rc_problem:
                    print_info_to_file(rcobject, "../results/rc_" + FILENAME + ".txt")


if __name__ == "__main__":
    main()
