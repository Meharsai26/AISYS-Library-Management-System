import { useState } from "react";
import { api, type Book, type Item, type Member } from "./api";
import "./App.css";

function App() {
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("demo_admin");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [books, setBooks] = useState<Book[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [title, setTitle] = useState("");
  const [accession, setAccession] = useState("");
  const [card, setCard] = useState("");
  const [memberName, setMemberName] = useState("");
  const [bookId, setBookId] = useState("");
  const [itemId, setItemId] = useState("");
  const [memberId, setMemberId] = useState("");
  const [loanId, setLoanId] = useState("");

  async function refresh(t = token) {
    const [b, i, m] = await Promise.all([
      api<Book[]>("/bibliographic-records", t),
      api<Item[]>("/items", t),
      api<Member[]>("/members", t),
    ]);
    setBooks(b);
    setItems(i);
    setMembers(m);
  }

  async function run(action: () => Promise<void>) {
    try {
      setMessage("");
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Operation failed");
    }
  }

  if (!token) {
    return (
      <main className="login">
        <h1>AISYS Library Management</h1>
        <p>RFID-enabled library system — synthetic prototype</p>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            const result = await api<{access_token:string}>(
              "/auth/login", undefined, "POST", {username, password}
            );
            setToken(result.access_token);
            setPassword("");
            setMessage("Login successful");
            await refresh(result.access_token);
          });
        }}>
          <input aria-label="Username" value={username}
            onChange={e => setUsername(e.target.value)} />
          <input aria-label="Password" type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Demo password" />
          <button type="submit">Sign in</button>
        </form>
        <p role="status">{message}</p>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <header>
        <div>
          <h1>AISYS Library Management</h1>
          <p>Local synthetic evaluation prototype</p>
        </div>
        <button onClick={() => void run(async () => {
          try { await api("/auth/logout", token, "POST"); }
          finally {
            setToken("");
            setBooks([]);
            setItems([]);
            setMembers([]);
          }
        })}>Logout</button>
      </header>

      <p role="status">{message}</p>

      <section>
        <h2>Catalog</h2>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            await api("/bibliographic-records", token, "POST", {title});
            setTitle("");
            await refresh();
            setMessage("Book created");
          });
        }}>
          <input placeholder="New book title" required value={title}
            onChange={e => setTitle(e.target.value)} />
          <button>Add Book</button>
        </form>
        <ul>{books.map(b => <li key={b.id}>{b.title}</li>)}</ul>
      </section>

      <section>
        <h2>Physical Library Items</h2>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            await api("/items", token, "POST", {
              bib_id: bookId, accession_number: accession
            });
            setAccession("");
            await refresh();
            setMessage("Item created");
          });
        }}>
          <select required value={bookId} onChange={e => setBookId(e.target.value)}>
            <option value="">Select Book</option>
            {books.map(b => <option key={b.id} value={b.id}>{b.title}</option>)}
          </select>
          <input required placeholder="Accession number" value={accession}
            onChange={e => setAccession(e.target.value)} />
          <button>Add Copy</button>
        </form>
        <ul>{items.map(i =>
          <li key={i.id}>{i.accession_number} — {i.status}</li>
        )}</ul>
      </section>

      <section>
        <h2>Members</h2>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            await api("/members", token, "POST", {
              card_number: card, display_name: memberName
            });
            setCard("");
            setMemberName("");
            await refresh();
            setMessage("Member created");
          });
        }}>
          <input required placeholder="Member card number" value={card}
            onChange={e => setCard(e.target.value)} />
          <input required placeholder="Member name" value={memberName}
            onChange={e => setMemberName(e.target.value)} />
          <button>Add Member</button>
        </form>
        <ul>{members.map(m =>
          <li key={m.id}>{m.display_name} — {m.card_number}</li>
        )}</ul>
      </section>

      <section>
        <h2>Circulation — Checkout</h2>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            const result = await api<{loan_id:string}>(
              "/loans/checkout", token, "POST",
              {item_id: itemId, member_id: memberId}
            );
            setLoanId(result.loan_id);
            await refresh();
            setMessage("Checkout successful");
          });
        }}>
          <select required value={itemId} onChange={e => setItemId(e.target.value)}>
            <option value="">Select available item</option>
            {items.filter(i => i.status === "AVAILABLE" && !i.is_reference)
              .map(i => <option key={i.id} value={i.id}>{i.accession_number}</option>)}
          </select>
          <select required value={memberId} onChange={e => setMemberId(e.target.value)}>
            <option value="">Select member</option>
            {members.filter(m => m.status === "ACTIVE")
              .map(m => <option key={m.id} value={m.id}>{m.display_name}</option>)}
          </select>
          <button>Checkout</button>
        </form>
      </section>

      <section>
        <h2>Return Loan</h2>
        <form onSubmit={e => {
          e.preventDefault();
          void run(async () => {
            await api(`/loans/${loanId}/return`, token, "POST");
            setLoanId("");
            await refresh();
            setMessage("Item returned");
          });
        }}>
          <input required placeholder="Loan ID" value={loanId}
            onChange={e => setLoanId(e.target.value)} />
          <button>Return</button>
        </form>
        <small>Loan ID is populated after checkout. It can also be pasted manually.</small>
      </section>
    </main>
  );
}

export default App;
