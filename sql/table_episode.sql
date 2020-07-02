create table episode
(
    id        int identity
        primary key,
    epNo      int not null,
    airDate   date,
    synopsis  varchar(100),
    guestNote varchar(100)
)
go