from datetime import datetime, timedelta
from services.library_service import calculate_late_fee_for_book
from database import insert_book, insert_borrow_record, get_book_by_isbn

def shelve(title: str, author: str, isbn: str, total: int, avail: int) -> int:
    """Insert a unique book and return its DB id."""
    insert_book(title, author, isbn, total, avail)
    return get_book_by_isbn(isbn)["id"]

def borrow_with_due(patron: str, *, book_id: int, days_overdue: int) -> None:
    """
    Create active borrow so days_overdue is how many days past due we are. DB respects the spec
    via due = borrow + 14 days.
    """
    now = datetime.now()
    due = now - timedelta(days=days_overdue)

    # due 14 days after borrow
    borrowed = due - timedelta(days=14)
    insert_borrow_record(patron, book_id, borrowed, due)


def test_fee_none_when_before_due():
    """
    Positive not overdue means fee 0.00 and days_overdue is also 0
    """
    book = shelve("Tensors in Teacups", "N. Chai", "9650000001017", total=2, avail=2)
    patron = "741963"

    # not overdo because marked as today
    borrow_with_due(patron, book_id=book, days_overdue=0)
    out = calculate_late_fee_for_book(patron, book)
    assert isinstance(out, dict)
    assert out.get("days_overdue") == 0
    assert round(float(out.get("fee_amount", 0.0)), 2) == 0.00

def test_fee_first_band_three_days():
    """
    Positive 3 days overdue is 3 * 0.50 = $1.50.
    """
    book = shelve("Hashmaps & Honey", "Q. Apiary", "9650000002028", total=1, avail=1)
    patron = "258147"
    borrow_with_due(patron, book_id=book, days_overdue=3)
    out = calculate_late_fee_for_book(patron, book)
    assert out.get("days_overdue") == 3
    assert round(float(out.get("fee_amount", -1.0)), 2) == 1.50

def test_fee_second_band_ten_days():
    """
    Positive 10 days overdue is 7*$0.50 + 3*$1.00 = $3.50 + $3.00 = $6.50.
    """
    book = shelve("Semaphore Sorbet", "M. Channel", "9650000003039", total=1, avail=1)
    patron = "864209"
    borrow_with_due(patron, book_id=book, days_overdue=10)
    out = calculate_late_fee_for_book(patron, book)
    assert out.get("days_overdue") == 10
    assert round(float(out.get("fee_amount", -1.0)), 2) == 6.50


def test_fee_capped_at_max():
    """
    Positive 40 days overdue would exceed the rate total $15 after cap.
    """
    book = shelve("Overdue Odyssey", "L. Late", "9650000004040", total=1, avail=1)
    patron = "505155"
    borrow_with_due(patron, book_id=book, days_overdue=40)
    out = calculate_late_fee_for_book(patron, book)
    assert out.get("days_overdue") == 40
    assert round(float(out.get("fee_amount", -1.0)), 2) == 15.00
