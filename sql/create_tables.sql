drop table if exists dbo.skull;
drop table if exists dbo.episode;

create table episode
(
    id        int identity primary key,
    epNo      int unique not null,
    airDate   date,
    synopsis  varchar(100),
    guestNote varchar(100)
)
go

-- auto-generated definition
create table skull
(
    id            int identity
        constraint skull_pk
            primary key nonclustered,
    member        text not null,
    time_appeared time not null,
    episode_no    int  not null
        constraint skull_episode_epNo_fk
            references episode (epNo)
)
go

create unique index skull_id_uindex
    on skull (id)
go

