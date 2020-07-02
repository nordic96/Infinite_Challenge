-- auto-generated definition
create table skull
(
    id            int identity
        constraint skull_pk
            primary key nonclustered,
    member        text not null,
    time_appeared time not null,
    episode_id    int  not null
        constraint skull_episode_id_fk
            references episode
)
go

create unique index skull_id_uindex
    on skull (id)
go