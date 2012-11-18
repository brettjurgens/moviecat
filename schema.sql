drop table if exists movies;
drop table if exists backdrops;
drop table if exists moviecat;

create table movies (
  id integer primary key autoincrement,
  tmdbid integer not null,
  title string not null,
  year integer not null,
  tagline string null,
  overview string null,
  runtime integer not null,
  rating real not null,
  homepage string null,
  trailer string null,
  location string not null,
  filename string null
);

create table backdrops (
  id integer primary key autoincrement,
  movieid integer not null
);

create table moviecat (
  id integer primary key autoincrement
);