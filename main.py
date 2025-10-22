from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Data Models
# -----------------------------
class Card(BaseModel):
    cardNumber: int
    isFlipped: bool
    isSelect: bool
    rowNumber: int
    colNumber: int
    isInBullHeadStack: bool
    isInDrawPile: bool


class State(BaseModel):
    hasStarted: bool
    playerTurn: bool
    hasEnded: bool
    playerScore: int
    aiScore: int
    playerWon: bool
    aiWon: bool
    aiAlgo: int
    cards: List[Card]
    r1Over: bool
    r2Over: bool
    r3Over: bool
    r1playerWon: bool
    r2playerWon: bool
    r3playerWon: bool
    r1playerScore: int
    r2playerScore: int
    r3playerScore: int
    r1aiScore: int
    r2aiScore: int
    r3aiScore: int
    round: int


# -----------------------------
# Utility functions
# -----------------------------
def getCards(state: State):
    return [_ for _ in state.cards]


def getGameStats(state: State):
    return {
        "hasStarted": state.hasStarted,
        "playerTurn": state.playerTurn,
        "hasEnded": state.hasEnded,
        "playerScore": state.playerScore,
        "aiScore": state.aiScore,
        "playerWon": state.playerWon,
        "aiWon": state.aiWon,
        "aiAlgo": state.aiAlgo,
        "r1Over": state.r1Over,
        "r2Over": state.r2Over,
        "r3Over": state.r3Over,
        "r1playerWon": state.r1playerWon,
        "r2playerWon": state.r2playerWon,
        "r3playerWon": state.r3playerWon,
        "r1playerScore": state.r1playerScore,
        "r2playerScore": state.r2playerScore,
        "r3playerScore": state.r3playerScore,
        "r1aiScore": state.r1aiScore,
        "r2aiScore": state.r2aiScore,
        "r3aiScore": state.r3aiScore,
        "round": state.round,
    }


def getCardInRow(cards, rowNumber):
    return [card for card in cards if card.rowNumber == rowNumber]


def getBullHeads(card: Card):
    num = card.cardNumber
    if num == 55:
        return 7
    if num % 10 == 0:
        return 3
    if num % 11 == 0:
        return 5
    if num % 5 == 0:
        return 2
    return 1


def getBullHeadScoreOfRow(cards, rowNumber):
    row = getCardInRow(cards, rowNumber)
    return sum(getBullHeads(card) for card in row)


# -----------------------------
# AI Logic
# -----------------------------
def aiCardTooLow(cards):
    row1, row2, row3, row4 = (
        getCardInRow(cards, 1),
        getCardInRow(cards, 2),
        getCardInRow(cards, 3),
        getCardInRow(cards, 4),
    )

    m1 = max((card.cardNumber for card in row1), default=0)
    m2 = max((card.cardNumber for card in row2), default=0)
    m3 = max((card.cardNumber for card in row3), default=0)
    m4 = max((card.cardNumber for card in row4), default=0)

    maxPlayerCard = max(
        (card.cardNumber for card in cards if card.rowNumber == 0 and not card.isInBullHeadStack),
        default=0,
    )

    return maxPlayerCard < min(m1, m2, m3, m4)


def updateRoundScore(gameStats, bullHeadScore):
    if gameStats["round"] == 1:
        gameStats["r1aiScore"] += bullHeadScore
    elif gameStats["round"] == 2:
        gameStats["r2aiScore"] += bullHeadScore
    else:
        gameStats["r3aiScore"] += bullHeadScore


def handleFullRow(cards, gameStats):
    minimumCardNumber = min(
        (card.cardNumber for card in cards if card.rowNumber == 0 and not card.isInBullHeadStack),
        default=0,
    )
    rowScores = [1, 2, 3, 4]
    rowScores.sort(key=lambda row: getBullHeadScoreOfRow(cards, row))

    for card in cards:
        if card.rowNumber == rowScores[0]:
            card.rowNumber = 0
            card.isInBullHeadStack = True
            bull = getBullHeads(card)
            gameStats["aiScore"] += bull
            updateRoundScore(gameStats, bull)

        if card.cardNumber == minimumCardNumber:
            card.rowNumber = rowScores[0]


def convertToJSON(gameStats, cards):
    return {
        **gameStats,
        "cards": [card.dict() for card in cards],
    }


def calc_next(state: State):
    cards = getCards(state)
    gameStats = getGameStats(state)

    if aiCardTooLow(cards):
        handleFullRow(cards, gameStats)
    else:
        ai_cards = [x for x in cards if x.rowNumber == 0 and not x.isInBullHeadStack]
        ai_cards.sort(key=lambda c: c.cardNumber)

        rows = [getCardInRow(cards, i) for i in range(1, 5)]
        maxis = [max((c.cardNumber for c in row), default=0) for row in rows]

        minirow = maxis.index(min(maxis)) + 1

        for aic in ai_cards:
            if aic.cardNumber > min(maxis):
                aic.rowNumber = minirow
                break

        # Handle full row (6 cards)
        if sum(1 for c in cards if c.rowNumber == minirow) == 6:
            for c in cards:
                if c.rowNumber == minirow:
                    c.rowNumber = 0
                    c.isInBullHeadStack = True
                    bull = getBullHeads(c)
                    updateRoundScore(gameStats, bull)
                    gameStats["aiScore"] += bull

    return convertToJSON(gameStats, cards)


# -----------------------------
# FastAPI Endpoint
# -----------------------------
@app.post("/")
async def process_request(state: State):
    new_state = calc_next(state)
    return new_state

