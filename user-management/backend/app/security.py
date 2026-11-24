"""Password hashing (and, from Phase 12, JWT helpers).

Argon2id is a one-way, salted and deliberately slow hash:
- one-way: the password cannot be recovered from the hash, only checked against it;
- salted: a random salt is stored inside each hash, so two accounts with the same
  password get different hashes and precomputed (rainbow) tables are useless;
- slow and memory-hard: each guess costs real time and RAM, so brute-forcing a
  stolen database is expensive.

The hash string records the algorithm, its parameters and the salt, e.g.
$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
"""

from argon2 import PasswordHasher

# The library defaults follow the RFC 9106 recommendations.
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)
