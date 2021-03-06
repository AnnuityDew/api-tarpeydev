"""initial state

Revision ID: 9426923edc92
Revises: 
Create Date: 2021-05-22 19:26:06.253135

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9426923edc92"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "backlog_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_title", sa.String(), nullable=True),
        sa.Column("sub_title", sa.String(), nullable=True),
        sa.Column("game_system", sa.String(), nullable=True),
        sa.Column("genre", sa.String(), nullable=True),
        sa.Column("dlc", sa.Boolean(), nullable=True),
        sa.Column("now_playing", sa.Boolean(), nullable=True),
        sa.Column(
            "game_status",
            sa.Enum(
                "NOT_STARTED",
                "STARTED",
                "BEATEN",
                "COMPLETED",
                "MASTERED",
                "INFINITE",
                "WISH_LIST",
                name="gamestatus",
            ),
            nullable=True,
        ),
        sa.Column("game_hours", sa.Integer(), nullable=True),
        sa.Column("game_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_playtime", sa.Boolean(), nullable=True),
        sa.Column("add_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("beat_date", sa.Date(), nullable=True),
        sa.Column("complete_date", sa.Date(), nullable=True),
        sa.Column("game_notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backlog_user_visuals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("treemap_json", sa.JSON(), nullable=True),
        sa.Column("bubbles_json", sa.JSON(), nullable=True),
        sa.Column("timeline_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cbb_player_seasons",
        sa.Column("StatID", sa.Integer(), nullable=False),
        sa.Column("TeamID", sa.Integer(), nullable=True),
        sa.Column("PlayerID", sa.Integer(), nullable=True),
        sa.Column("SeasonType", sa.Integer(), nullable=True),
        sa.Column("Season", sa.String(), nullable=True),
        sa.Column("Name", sa.String(), nullable=True),
        sa.Column("Team", sa.String(), nullable=True),
        sa.Column("Position", sa.String(), nullable=True),
        sa.Column("Games", sa.Integer(), nullable=True),
        sa.Column("FantasyPoints", sa.Float(), nullable=True),
        sa.Column("Minutes", sa.Integer(), nullable=True),
        sa.Column("FieldGoalsMade", sa.Integer(), nullable=True),
        sa.Column("FieldGoalsAttempted", sa.Integer(), nullable=True),
        sa.Column("FieldGoalsPercentage", sa.Float(), nullable=True),
        sa.Column("TwoPointersMade", sa.Integer(), nullable=True),
        sa.Column("TwoPointersAttempted", sa.Integer(), nullable=True),
        sa.Column("TwoPointersPercentage", sa.Float(), nullable=True),
        sa.Column("ThreePointersMade", sa.Integer(), nullable=True),
        sa.Column("ThreePointersAttempted", sa.Integer(), nullable=True),
        sa.Column("ThreePointersPercentage", sa.Float(), nullable=True),
        sa.Column("FreeThrowsMade", sa.Integer(), nullable=True),
        sa.Column("FreeThrowsAttempted", sa.Integer(), nullable=True),
        sa.Column("FreeThrowsPercentage", sa.Float(), nullable=True),
        sa.Column("OffensiveRebounds", sa.Integer(), nullable=True),
        sa.Column("DefensiveRebounds", sa.Integer(), nullable=True),
        sa.Column("Rebounds", sa.Integer(), nullable=True),
        sa.Column("Assists", sa.Integer(), nullable=True),
        sa.Column("Steals", sa.Integer(), nullable=True),
        sa.Column("BlockedShots", sa.Integer(), nullable=True),
        sa.Column("Turnovers", sa.Integer(), nullable=True),
        sa.Column("PersonalFouls", sa.Integer(), nullable=True),
        sa.Column("Points", sa.Integer(), nullable=True),
        sa.Column("FantasyPointsFanDuel", sa.Float(), nullable=True),
        sa.Column("FantasyPointsDraftKings", sa.Float(), nullable=True),
        sa.Column("two_attempt_chance", sa.Float(), nullable=True),
        sa.Column("two_chance", sa.Float(), nullable=True),
        sa.Column("three_chance", sa.Float(), nullable=True),
        sa.Column("ft_chance", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("StatID"),
    )
    op.create_table(
        "cbb_simulated_brackets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bracket", sa.JSON(), nullable=True),
        sa.Column(
            "flavor",
            sa.Enum("NONE", "MILD", "MEDIUM", "MAX", name="bracketflavor"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cbb_simulation_distributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("away_key", sa.String(), nullable=True),
        sa.Column("home_key", sa.String(), nullable=True),
        sa.Column("season", sa.String(), nullable=True),
        sa.Column("home_win_chance_max", sa.Float(), nullable=True),
        sa.Column("max_margin_top", sa.Integer(), nullable=True),
        sa.Column("max_margin_bottom", sa.Integer(), nullable=True),
        sa.Column("home_win_chance_medium", sa.Float(), nullable=True),
        sa.Column("medium_margin_top", sa.Integer(), nullable=True),
        sa.Column("medium_margin_bottom", sa.Integer(), nullable=True),
        sa.Column("home_win_chance_mild", sa.Float(), nullable=True),
        sa.Column("mild_margin_top", sa.Integer(), nullable=True),
        sa.Column("mild_margin_bottom", sa.Integer(), nullable=True),
        sa.Column("home_win_chance_median", sa.Float(), nullable=True),
        sa.Column("median_margin_top", sa.Integer(), nullable=True),
        sa.Column("median_margin_bottom", sa.Integer(), nullable=True),
        sa.Column("median_margin", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cbb_simulation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_summary", sa.JSON(), nullable=True),
        sa.Column("team_box_score", sa.JSON(), nullable=True),
        sa.Column("full_box_score", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "cbb_teams",
        sa.Column("SeasonTeamID", sa.BigInteger(), nullable=False),
        sa.Column("Key", sa.String(), nullable=True),
        sa.Column("School", sa.String(), nullable=True),
        sa.Column("Name", sa.String(), nullable=True),
        sa.Column("GlobalTeamID", sa.Integer(), nullable=True),
        sa.Column("Conference", sa.String(), nullable=True),
        sa.Column("TeamLogoUrl", sa.String(), nullable=True),
        sa.Column("ShortDisplayName", sa.String(), nullable=True),
        sa.Column("Stadium", sa.JSON(), nullable=True),
        sa.Column("Season", sa.String(), nullable=True),
        sa.Column("Rk", sa.Integer(), nullable=True),
        sa.Column("Conf", sa.String(), nullable=True),
        sa.Column("W", sa.Integer(), nullable=True),
        sa.Column("L", sa.Integer(), nullable=True),
        sa.Column("AdjEM", sa.Float(), nullable=True),
        sa.Column("AdjO", sa.Float(), nullable=True),
        sa.Column("AdjD", sa.Float(), nullable=True),
        sa.Column("AdjT", sa.Float(), nullable=True),
        sa.Column("Luck", sa.Float(), nullable=True),
        sa.Column("OppAdjEM", sa.Float(), nullable=True),
        sa.Column("OppO", sa.Float(), nullable=True),
        sa.Column("OppD", sa.Float(), nullable=True),
        sa.Column("NCAdjEM", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("SeasonTeamID"),
    )
    op.create_table(
        "ml_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("away", sa.String(), nullable=True),
        sa.Column(
            "away_nick",
            sa.Enum(
                "TARPEY",
                "CHRISTIAN",
                "NEEL",
                "BRANDO",
                "DEBBIE",
                "DANNY",
                "MILDRED",
                "HARDY",
                "TOMMY",
                "BRYANT",
                "KINDY",
                "SENDZIK",
                "SAMIK",
                "STEPHANIE",
                "DEBSKI",
                "BEN",
                "ARTHUR",
                "CONTI",
                "FONTI",
                "FRANK",
                "MIKE",
                "PATRICK",
                "CHARLES",
                "JAKE",
                "BRAD",
                "BYE",
                name="nickname",
            ),
            nullable=True,
        ),
        sa.Column("away_score", sa.Float(), nullable=True),
        sa.Column("home", sa.String(), nullable=True),
        sa.Column(
            "home_nick",
            sa.Enum(
                "TARPEY",
                "CHRISTIAN",
                "NEEL",
                "BRANDO",
                "DEBBIE",
                "DANNY",
                "MILDRED",
                "HARDY",
                "TOMMY",
                "BRYANT",
                "KINDY",
                "SENDZIK",
                "SAMIK",
                "STEPHANIE",
                "DEBSKI",
                "BEN",
                "ARTHUR",
                "CONTI",
                "FONTI",
                "FRANK",
                "MIKE",
                "PATRICK",
                "CHARLES",
                "JAKE",
                "BRAD",
                "BYE",
                name="nickname",
            ),
            nullable=True,
        ),
        sa.Column("home_score", sa.Float(), nullable=True),
        sa.Column("week_start", sa.Integer(), nullable=True),
        sa.Column("week_end", sa.Integer(), nullable=True),
        sa.Column(
            "season",
            sa.Enum(
                "SEASON1",
                "SEASON2",
                "SEASON3",
                "SEASON4",
                "SEASON5",
                "SEASON6",
                "SEASON7",
                "SEASON8",
                name="mlseason",
            ),
            nullable=True,
        ),
        sa.Column(
            "playoff",
            sa.Enum("REGULAR", "PLAYOFF", "LOSERS", name="mlplayoff"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ml_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "season",
            sa.Enum(
                "SEASON1",
                "SEASON2",
                "SEASON3",
                "SEASON4",
                "SEASON5",
                "SEASON6",
                "SEASON7",
                "SEASON8",
                name="mlseason",
            ),
            nullable=True,
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ml_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("division", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column(
            "nick_name",
            sa.Enum(
                "TARPEY",
                "CHRISTIAN",
                "NEEL",
                "BRANDO",
                "DEBBIE",
                "DANNY",
                "MILDRED",
                "HARDY",
                "TOMMY",
                "BRYANT",
                "KINDY",
                "SENDZIK",
                "SAMIK",
                "STEPHANIE",
                "DEBSKI",
                "BEN",
                "ARTHUR",
                "CONTI",
                "FONTI",
                "FRANK",
                "MIKE",
                "PATRICK",
                "CHARLES",
                "JAKE",
                "BRAD",
                "BYE",
                name="nickname",
            ),
            nullable=True,
        ),
        sa.Column(
            "season",
            sa.Enum(
                "SEASON1",
                "SEASON2",
                "SEASON3",
                "SEASON4",
                "SEASON5",
                "SEASON6",
                "SEASON7",
                "SEASON8",
                name="mlseason",
            ),
            nullable=True,
        ),
        sa.Column("playoff_rank", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quote_text", sa.String(), nullable=True),
        sa.Column("quote_origin", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("quotes")
    op.drop_table("ml_teams")
    op.drop_table("ml_notes")
    op.drop_table("ml_games")
    op.drop_table("cbb_teams")
    op.drop_table("cbb_simulation_runs")
    op.drop_table("cbb_simulation_distributions")
    op.drop_table("cbb_simulated_brackets")
    op.drop_table("cbb_player_seasons")
    op.drop_table("backlog_user_visuals")
    op.drop_table("backlog_games")
    # ### end Alembic commands ###
