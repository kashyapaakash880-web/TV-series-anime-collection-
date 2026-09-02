from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float , func , or_
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField ,FloatField
from wtforms.validators import DataRequired
import requests
from collections import Counter
from dotenv import load_dotenv
import os


load_dotenv()

API_KEY = os.getenv("API_KEY")

URL = "https://api.themoviedb.org/3/search/tv"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
Bootstrap5(app)

# CREATE DB
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# configure the SQLite database, relative to the app instance folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TV-Series-and-anime.db'

# initialize the app with the extension
db.init_app(app)

# CREATE TABLE

"""Subclass db.Model to define a model class. The model will generate a table name 
by converting the CamelCase class name to snake_case."""

class TVSeries(db.Model):
    id:Mapped[int] = mapped_column(Integer, primary_key=True)
    title:Mapped[str] = mapped_column(String)
    year:Mapped[int] = mapped_column(Integer)
    description:Mapped[str] = mapped_column(String(250))
    rating:Mapped[float] = mapped_column(Float)
    ranking:Mapped[int] = mapped_column(Integer)
    review : Mapped[str] = mapped_column(String(250))
    img_url:Mapped[str] = mapped_column(String(500))
    type = db.Column(db.String(20))
    genre = db.Column(db.String(250))
    tagline = db.Column(db.String(250))

class Series(FlaskForm):
    title = StringField('TV Series', validators=[DataRequired()])
    submit = SubmitField("Add Shows")

class EditingData(FlaskForm):
    ranking = FloatField(label="Your Ranking ", validators=[DataRequired()])
    review = StringField(label="Your Review", validators=[DataRequired()])
    rating = FloatField(label="Your Rating", validators=[DataRequired()])
    submit = SubmitField(label="Submit")

# Now save the database
with app.app_context():
    db.create_all()



@app.route("/")
def home():
    series = db.session.execute(db.select(TVSeries).order_by(TVSeries.ranking.asc())).scalars().all()
    """Dashboard data """
    total_shows = db.session.query(TVSeries).count()
    anime_count = sum(1 for show in series if show.type == "Anime")
    tv_count = sum(1 for show in series if show.type =="TV Show")
    average = db.session.query(func.avg(TVSeries.rating)).scalar()
    averages = round(average, 2)

    genres = []

    for show in series:
        if show.genre:
            genres.extend(show.genre.split(","))

    favorite_genre = Counter(genres).most_common(1)[0][0] if genres else "None"

    return render_template("index.html",
                           series=series,
                           total_shows=total_shows,
                           anime=anime_count,
                           shows=tv_count,
                           average=averages,
                           favorite_genre=favorite_genre,)

@app.route("/find")
def find():

    Series_title = request.args.get("title")

    headers = {
        "Authorization": API_KEY
    }

    response = requests.get(URL, headers=headers ,params={"query":Series_title})

    data = response.json()

    return render_template(
        "select.html",
        series=data["results"]
    )

@app.route("/add", methods=["GET", "POST"])
def add():
    form = Series()

    if form.validate_on_submit():
        return redirect(url_for("find",title=form.title.data))

    return render_template("add.html",form=form)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    series_id = request.args.get("id")
    tv_series = db.get_or_404(TVSeries, series_id)

    form = EditingData()

    if form.validate_on_submit():
        tv_series.ranking = request.form.get("ranking")
        tv_series.rating = request.form.get("rating")
        tv_series.review = request.form.get("review")
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", form=form, series=tv_series)


@app.route("/delete")
def delete():
    series_id = request.args.get("id")
    delete_series = db.get_or_404(TVSeries, series_id)
    db.session.delete(delete_series)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/add_shows")
def add_shows():
    series_id = request.args.get("id")

    headers = {
        "Authorization": API_KEY
    }

    response = requests.get(
        f"https://api.themoviedb.org/3/tv/{series_id}",
        headers=headers
    )

    data = response.json()

    genres = ", ".join([genre["name"] for genre in data["genres"]])

    show_type = "Anime" if "Animation" in genres else "TV Show"

    new_shows = TVSeries(
        title=data["name"],
        year=int(data["first_air_date"][:4]),
        description=data["overview"],
        rating=0.0,
        ranking=0,
        review="",
        img_url=f"https://image.tmdb.org/t/p/w500{data['poster_path']}",
        type=show_type,
        genre=genres,
        tagline=data["tagline"],
    )

    db.session.add(new_shows)
    db.session.commit()

    return redirect(url_for("edit", id=new_shows.id))



@app.route("/search")
def search():
    query = request.args.get("query")

    results = db.session.execute(
        db.select(TVSeries).where(
            or_(
                TVSeries.title.ilike(f"%{query}%"),
                TVSeries.genre.ilike(f"%{query}%"),
                TVSeries.type.ilike(f"%{query}%")
            )
        )
    ).scalars().all()

    return render_template(
        "search.html",
        results=results,
        query=query
    )
if __name__ == '__main__':
    app.run(debug=True)
