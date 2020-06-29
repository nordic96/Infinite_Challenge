CREATE TABLE Episode (
      id INT NOT NULL IDENTITY PRIMARY KEY,
      epNo INT NOT NULL,
      airDate DATE,
      synopsis VARCHAR(100),
      guestNote VARCHAR(100)
);