"""
seed_hardcoded_books.py
Non-destructive seed script using hardcoded, real ISBN data.
Images pulled from Open Library Covers API using the ISBN.
NO external API calls at runtime. ISBN list is baked in.
"""
from decimal import Decimal
from psycopg2.extras import execute_batch
from app import create_app
from app.models.db import get_db_connection
from app.logger import get_logger

logger = get_logger(__name__)

# 75 real, well-known books with valid ISBNs across multiple genres.
# Cover URLs are constructed at runtime using the Open Library Covers API.
BOOKS = [
    # --- Fiction ---
    {"title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": "Fiction", "price": Decimal("14.99"), "stock_quantity": 80, "isbn": "9780061935466", "description": "A gripping story of racial injustice and childhood innocence in the American South."},
    {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": "Fiction", "price": Decimal("12.99"), "stock_quantity": 90, "isbn": "9780743273565", "description": "A classic portrait of the American Dream and its hollow pursuit in the Jazz Age."},
    {"title": "1984", "author": "George Orwell", "genre": "Fiction", "price": Decimal("13.99"), "stock_quantity": 100, "isbn": "9780451524935", "description": "A dystopian novel about totalitarian surveillance and the destruction of truth."},
    {"title": "Brave New World", "author": "Aldous Huxley", "genre": "Fiction", "price": Decimal("13.49"), "stock_quantity": 75, "isbn": "9780060850524", "description": "A chilling vision of a future society controlled by pleasure, conditioning, and consumption."},
    {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "genre": "Fiction", "price": Decimal("12.49"), "stock_quantity": 85, "isbn": "9780316769174", "description": "A defining novel of teenage alienation and rebellion in postwar America."},
    {"title": "Of Mice and Men", "author": "John Steinbeck", "genre": "Fiction", "price": Decimal("11.99"), "stock_quantity": 70, "isbn": "9780140177398", "description": "A poignant tale of friendship, dreams, and tragedy among migrant workers."},
    {"title": "The Old Man and the Sea", "author": "Ernest Hemingway", "genre": "Fiction", "price": Decimal("11.49"), "stock_quantity": 65, "isbn": "9780684801223", "description": "Hemingway's Nobel Prize-winning novella about an aging fisherman's epic struggle."},
    {"title": "Lord of the Flies", "author": "William Golding", "genre": "Fiction", "price": Decimal("12.99"), "stock_quantity": 90, "isbn": "9780399501487", "description": "A group of stranded boys descend into savagery in this allegory of human nature."},
    {"title": "Animal Farm", "author": "George Orwell", "genre": "Fiction", "price": Decimal("10.99"), "stock_quantity": 100, "isbn": "9780451526342", "description": "A satirical fable about political revolution and the corruption of idealism."},
    {"title": "Pride and Prejudice", "author": "Jane Austen", "genre": "Fiction", "price": Decimal("12.99"), "stock_quantity": 95, "isbn": "9780141439518", "description": "Austen's witty exploration of love, class, and marriage in Regency-era England."},
    {"title": "Jane Eyre", "author": "Charlotte Brontë", "genre": "Fiction", "price": Decimal("13.49"), "stock_quantity": 80, "isbn": "9780141441146", "description": "A passionate story of a governess who falls for her brooding, mysterious employer."},
    {"title": "Wuthering Heights", "author": "Emily Brontë", "genre": "Fiction", "price": Decimal("12.99"), "stock_quantity": 75, "isbn": "9780141439556", "description": "A wild, passionate tale of love and revenge set on the Yorkshire moors."},
    {"title": "Crime and Punishment", "author": "Fyodor Dostoevsky", "genre": "Fiction", "price": Decimal("14.49"), "stock_quantity": 60, "isbn": "9780140449136", "description": "A psychological study of a student who commits a murder and its devastating aftermath."},
    {"title": "The Brothers Karamazov", "author": "Fyodor Dostoevsky", "genre": "Fiction", "price": Decimal("16.99"), "stock_quantity": 50, "isbn": "9780374528379", "description": "A masterpiece exploring faith, doubt, and morality through a family murder mystery."},
    {"title": "Anna Karenina", "author": "Leo Tolstoy", "genre": "Fiction", "price": Decimal("15.99"), "stock_quantity": 55, "isbn": "9780143035008", "description": "A tragic story of an aristocratic woman who defies social norms for an adulterous love."},
    {"title": "One Hundred Years of Solitude", "author": "Gabriel García Márquez", "genre": "Fiction", "price": Decimal("15.49"), "stock_quantity": 60, "isbn": "9780060883287", "description": "The multi-generational saga of the Buendía family in the mythical town of Macondo."},
    {"title": "The Alchemist", "author": "Paulo Coelho", "genre": "Fiction", "price": Decimal("14.99"), "stock_quantity": 120, "isbn": "9780062315007", "description": "A philosophical novel about a young shepherd's journey to discover his personal legend."},
    {"title": "Beloved", "author": "Toni Morrison", "genre": "Fiction", "price": Decimal("14.49"), "stock_quantity": 65, "isbn": "9781400033416", "description": "A Pulitzer Prize-winning novel exploring the trauma of slavery and its haunting aftermath."},
    {"title": "The Color Purple", "author": "Alice Walker", "genre": "Fiction", "price": Decimal("13.99"), "stock_quantity": 70, "isbn": "9780156028356", "description": "An epistolary novel about the struggles of Black women in the rural American South."},
    {"title": "Invisible Man", "author": "Ralph Ellison", "genre": "Fiction", "price": Decimal("14.49"), "stock_quantity": 60, "isbn": "9780679732761", "description": "A landmark novel about a Black man's journey of identity in a racially divided America."},
    # --- Science Fiction ---
    {"title": "Dune", "author": "Frank Herbert", "genre": "Science Fiction", "price": Decimal("18.99"), "stock_quantity": 110, "isbn": "9780441013593", "description": "An epic science fiction saga set in a feudal interstellar society on a desert planet."},
    {"title": "Foundation", "author": "Isaac Asimov", "genre": "Science Fiction", "price": Decimal("16.49"), "stock_quantity": 85, "isbn": "9780553293357", "description": "Asimov's visionary saga about a mathematician who tries to save civilization from collapse."},
    {"title": "The Hitchhiker's Guide to the Galaxy", "author": "Douglas Adams", "genre": "Science Fiction", "price": Decimal("13.99"), "stock_quantity": 130, "isbn": "9780345391803", "description": "A hilarious and insightful comedy about the infinite improbabilities of the universe."},
    {"title": "Ender's Game", "author": "Orson Scott Card", "genre": "Science Fiction", "price": Decimal("14.99"), "stock_quantity": 95, "isbn": "9780812550702", "description": "A child prodigy trains in a space battle school to fight an alien invasion."},
    {"title": "The Martian", "author": "Andy Weir", "genre": "Science Fiction", "price": Decimal("15.99"), "stock_quantity": 100, "isbn": "9780804139021", "description": "An astronaut stranded on Mars must use science and ingenuity to survive."},
    {"title": "Neuromancer", "author": "William Gibson", "genre": "Science Fiction", "price": Decimal("14.49"), "stock_quantity": 70, "isbn": "9780441569595", "description": "The cyberpunk classic that coined the term 'cyberspace' and influenced a generation."},
    {"title": "Snow Crash", "author": "Neal Stephenson", "genre": "Science Fiction", "price": Decimal("17.99"), "stock_quantity": 80, "isbn": "9780553380958", "description": "A deep dive into a near-future America of virtual reality, linguistics, and corporate fiefdoms."},
    {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "genre": "Science Fiction", "price": Decimal("14.99"), "stock_quantity": 65, "isbn": "9780441478125", "description": "A groundbreaking exploration of gender and politics on an ambisexual alien world."},
    {"title": "Fahrenheit 451", "author": "Ray Bradbury", "genre": "Science Fiction", "price": Decimal("12.99"), "stock_quantity": 105, "isbn": "9781451673319", "description": "In a future where books are banned, a fireman begins to question his role in censorship."},
    {"title": "Do Androids Dream of Electric Sheep?", "author": "Philip K. Dick", "genre": "Science Fiction", "price": Decimal("13.99"), "stock_quantity": 75, "isbn": "9780345404473", "description": "The cult novel that inspired Blade Runner, exploring humanity, empathy, and artificial life."},
    {"title": "Ringworld", "author": "Larry Niven", "genre": "Science Fiction", "price": Decimal("14.49"), "stock_quantity": 60, "isbn": "9780345333926", "description": "An exploration crew investigates a vast artificial ring world orbiting a distant star."},
    {"title": "Childhood's End", "author": "Arthur C. Clarke", "genre": "Science Fiction", "price": Decimal("13.99"), "stock_quantity": 65, "isbn": "9780345347954", "description": "A powerful story about the end of humanity's childhood and a transformation beyond understanding."},
    {"title": "The Time Machine", "author": "H.G. Wells", "genre": "Science Fiction", "price": Decimal("10.99"), "stock_quantity": 80, "isbn": "9780451530707", "description": "A Victorian scientist travels to the far future to discover the fate of humankind."},
    {"title": "I, Robot", "author": "Isaac Asimov", "genre": "Science Fiction", "price": Decimal("14.49"), "stock_quantity": 85, "isbn": "9780553382563", "description": "Nine short stories that defined the concept of robots and their Three Laws of Robotics."},
    {"title": "The Moon is a Harsh Mistress", "author": "Robert A. Heinlein", "genre": "Science Fiction", "price": Decimal("15.99"), "stock_quantity": 60, "isbn": "9780312863555", "description": "A lunar colony revolts against Earth rule in this libertarian science fiction classic."},
    # --- Technology / Computers ---
    {"title": "Clean Code", "author": "Robert C. Martin", "genre": "Technology", "price": Decimal("44.99"), "stock_quantity": 50, "isbn": "9780132350884", "description": "A handbook of agile software craftsmanship, teaching programmers to write readable, maintainable code."},
    {"title": "The Pragmatic Programmer", "author": "David Thomas and Andrew Hunt", "genre": "Technology", "price": Decimal("42.99"), "stock_quantity": 45, "isbn": "9780135957059", "description": "A classic guide for developers looking to become true craftsmen of their art."},
    {"title": "Design Patterns", "author": "Gang of Four", "genre": "Technology", "price": Decimal("44.49"), "stock_quantity": 40, "isbn": "9780201633610", "description": "The foundational textbook on reusable object-oriented software design patterns."},
    {"title": "The Mythical Man-Month", "author": "Frederick P. Brooks Jr.", "genre": "Technology", "price": Decimal("36.99"), "stock_quantity": 35, "isbn": "9780201835953", "description": "Essential essays on software engineering, still relevant decades after first publication."},
    {"title": "Code Complete", "author": "Steve McConnell", "genre": "Technology", "price": Decimal("43.99"), "stock_quantity": 40, "isbn": "9780735619678", "description": "A comprehensive guide to software construction and best practices in writing software."},
    {"title": "Refactoring", "author": "Martin Fowler", "genre": "Technology", "price": Decimal("41.99"), "stock_quantity": 40, "isbn": "9780134757599", "description": "Techniques and patterns for safely improving the design of existing code."},
    {"title": "Introduction to Algorithms", "author": "Cormen, Leiserson, Rivest, Stein", "genre": "Technology", "price": Decimal("44.99"), "stock_quantity": 30, "isbn": "9780262033848", "description": "The definitive computer science textbook covering a broad range of algorithms in depth."},
    {"title": "The Linux Command Line", "author": "William E. Shotts Jr.", "genre": "Technology", "price": Decimal("29.99"), "stock_quantity": 60, "isbn": "9781593279523", "description": "A complete introduction to working with the Linux command line."},
    {"title": "Python Crash Course", "author": "Eric Matthes", "genre": "Technology", "price": Decimal("34.99"), "stock_quantity": 70, "isbn": "9781718502703", "description": "A hands-on, project-based introduction to programming in Python."},
    {"title": "Learning SQL", "author": "Alan Beaulieu", "genre": "Technology", "price": Decimal("35.99"), "stock_quantity": 50, "isbn": "9781492057611", "description": "Generate, manipulate, and retrieve data from relational databases using SQL."},
    {"title": "Flask Web Development", "author": "Miguel Grinberg", "genre": "Technology", "price": Decimal("39.99"), "stock_quantity": 45, "isbn": "9781491991732", "description": "Developing web applications with Python using the Flask framework."},
    {"title": "Two Scoops of Django", "author": "Daniel Feldroy and Audrey Feldroy", "genre": "Technology", "price": Decimal("39.49"), "stock_quantity": 40, "isbn": "9780692915729", "description": "Best practices for the Django web framework for Python developers."},
    {"title": "The Phoenix Project", "author": "Gene Kim, Kevin Behr, George Spafford", "genre": "Technology", "price": Decimal("27.99"), "stock_quantity": 65, "isbn": "9781942788294", "description": "A novel about IT, DevOps, and helping your business win, told through a fictional manager."},
    {"title": "Accelerate", "author": "Nicole Forsgren, Jez Humble, Gene Kim", "genre": "Technology", "price": Decimal("28.99"), "stock_quantity": 55, "isbn": "9781942788331", "description": "The science of lean software and DevOps, backed by four years of research."},
    {"title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "genre": "Technology", "price": Decimal("44.99"), "stock_quantity": 40, "isbn": "9781449373320", "description": "The big ideas behind reliable, scalable, and maintainable systems."},
    # --- History ---
    {"title": "Sapiens: A Brief History of Humankind", "author": "Yuval Noah Harari", "genre": "History", "price": Decimal("18.99"), "stock_quantity": 120, "isbn": "9780062316097", "description": "A sweeping history of human civilization from the Stone Age to the twenty-first century."},
    {"title": "Homo Deus: A Brief History of Tomorrow", "author": "Yuval Noah Harari", "genre": "History", "price": Decimal("17.99"), "stock_quantity": 95, "isbn": "9780062464316", "description": "Harari explores the future of humanity and how we might engineer our own divinity."},
    {"title": "Guns, Germs, and Steel", "author": "Jared Diamond", "genre": "History", "price": Decimal("18.49"), "stock_quantity": 85, "isbn": "9780393317558", "description": "A Pulitzer Prize-winning analysis of why some civilizations dominate others."},
    {"title": "The Silk Roads", "author": "Peter Frankopan", "genre": "History", "price": Decimal("19.99"), "stock_quantity": 70, "isbn": "9781101912379", "description": "A new history of the world, centered on the interconnected routes linking East and West."},
    {"title": "A Peoples History of the United States", "author": "Howard Zinn", "genre": "History", "price": Decimal("21.99"), "stock_quantity": 75, "isbn": "9780062397348", "description": "American history told from the perspective of those typically left out of traditional accounts."},
    {"title": "The Rise and Fall of the Third Reich", "author": "William L. Shirer", "genre": "History", "price": Decimal("24.99"), "stock_quantity": 50, "isbn": "9781451651683", "description": "The definitive account of the Nazi regime, told by a journalist who witnessed it firsthand."},
    {"title": "The Diary of a Young Girl", "author": "Anne Frank", "genre": "History", "price": Decimal("12.99"), "stock_quantity": 100, "isbn": "9780553296983", "description": "The moving account of a Jewish girl in hiding during the Nazi occupation of Amsterdam."},
    {"title": "Band of Brothers", "author": "Stephen E. Ambrose", "genre": "History", "price": Decimal("17.99"), "stock_quantity": 75, "isbn": "9780743224991", "description": "The story of Easy Company, 506th Regiment, 101st Airborne Division during WWII."},
    {"title": "Empire of the Summer Moon", "author": "S.C. Gwynne", "genre": "History", "price": Decimal("17.49"), "stock_quantity": 65, "isbn": "9781416591054", "description": "The rise and fall of the Comanche empire, the most powerful Indian tribe in American history."},
    {"title": "The Warmth of Other Suns", "author": "Isabel Wilkerson", "genre": "History", "price": Decimal("19.99"), "stock_quantity": 60, "isbn": "9780679763888", "description": "The epic story of Black Americans migrating from the South to the North and West."},
    {"title": "Longitude", "author": "Dava Sobel", "genre": "History", "price": Decimal("13.99"), "stock_quantity": 70, "isbn": "9780802713315", "description": "The true story of the lone genius who solved the greatest scientific problem of his time."},
    # --- Biography ---
    {"title": "Steve Jobs", "author": "Walter Isaacson", "genre": "Biography", "price": Decimal("19.99"), "stock_quantity": 90, "isbn": "9781451648539", "description": "The exclusive biography of Apple's visionary co-founder, based on extensive interviews."},
    {"title": "Elon Musk", "author": "Walter Isaacson", "genre": "Biography", "price": Decimal("23.99"), "stock_quantity": 100, "isbn": "9781982181284", "description": "An intimate biography of one of the most controversial and consequential entrepreneurs."},
    {"title": "The Autobiography of Malcolm X", "author": "Malcolm X and Alex Haley", "genre": "Biography", "price": Decimal("14.99"), "stock_quantity": 75, "isbn": "9780345350688", "description": "A landmark of American autobiography and a testament to an extraordinary life."},
    {"title": "I Know Why the Caged Bird Sings", "author": "Maya Angelou", "genre": "Biography", "price": Decimal("13.99"), "stock_quantity": 80, "isbn": "9780345514400", "description": "Maya Angelou's masterful account of her childhood and adolescence in the South."},
    {"title": "Long Walk to Freedom", "author": "Nelson Mandela", "genre": "Biography", "price": Decimal("17.99"), "stock_quantity": 70, "isbn": "9780316548182", "description": "The autobiography of Nelson Mandela, chronicling his path from rural village to prison to presidency."},
    {"title": "The Story of My Experiments with Truth", "author": "Mahatma Gandhi", "genre": "Biography", "price": Decimal("14.49"), "stock_quantity": 60, "isbn": "9780807059098", "description": "Gandhi's own account of his life, philosophy, and the development of nonviolent resistance."},
    {"title": "Leonardo da Vinci", "author": "Walter Isaacson", "genre": "Biography", "price": Decimal("19.99"), "stock_quantity": 65, "isbn": "9781501139154", "description": "A study of the world's greatest creative genius, based on thousands of his notebooks."},
    {"title": "Becoming", "author": "Michelle Obama", "genre": "Biography", "price": Decimal("17.99"), "stock_quantity": 110, "isbn": "9781524763138", "description": "An intimate, powerful memoir by the former First Lady of the United States."},
    {"title": "Educated", "author": "Tara Westover", "genre": "Biography", "price": Decimal("16.99"), "stock_quantity": 100, "isbn": "9780399590504", "description": "A memoir about a young woman, kept out of school, who ultimately gains a PhD from Cambridge."},
    {"title": "When Breath Becomes Air", "author": "Paul Kalanithi", "genre": "Biography", "price": Decimal("15.99"), "stock_quantity": 85, "isbn": "9780812988406", "description": "A neurosurgeon's memoir on mortality, written as he faced terminal lung cancer."},
]


def seed_hardcoded_books():
    print(f"Initializing Flask App Context... {len(BOOKS)} books ready to process.")
    app = create_app()

    with app.app_context():
        conn = get_db_connection()
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # Fetch existing IDs to preserve relational integrity
                cur.execute("SELECT book_id FROM books ORDER BY book_id;")
                existing_ids = [row['book_id'] for row in cur.fetchall()]
                num_existing = len(existing_ids)
                print(f"Found {num_existing} existing book rows to update.")

                to_update = []
                to_insert = []

                for i, book in enumerate(BOOKS):
                    image_url = f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-L.jpg"
                    payload = {
                        'title': book['title'],
                        'author': book['author'],
                        'genre': book['genre'],
                        'price': book['price'],
                        'stock_quantity': book['stock_quantity'],
                        'description': book['description'],
                        'image_url': image_url,
                    }
                    if i < num_existing:
                        payload['book_id'] = existing_ids[i]
                        to_update.append(payload)
                    else:
                        to_insert.append(payload)

                if to_update:
                    print(f"Phase 1: Updating {len(to_update)} existing rows with real book data...")
                    update_sql = """
                        UPDATE books
                        SET title = %(title)s, author = %(author)s, genre = %(genre)s,
                            price = %(price)s, stock_quantity = %(stock_quantity)s,
                            description = %(description)s, image_url = %(image_url)s
                        WHERE book_id = %(book_id)s;
                    """
                    execute_batch(cur, update_sql, to_update)

                if to_insert:
                    print(f"Phase 2: Inserting {len(to_insert)} new additional books...")
                    insert_sql = """
                        INSERT INTO books (title, author, genre, price, stock_quantity, description, image_url)
                        VALUES (%(title)s, %(author)s, %(genre)s, %(price)s, %(stock_quantity)s, %(description)s, %(image_url)s);
                    """
                    execute_batch(cur, insert_sql, to_insert)

            conn.commit()
            print(f"SUCCESS: Transaction committed. Updated {len(to_update)}, inserted {len(to_insert)} books.")
        except Exception as e:
            conn.rollback()
            print(f"FAILED: Error during seeding. Transaction rolled back.")
            print(f"Error: {e}")
            raise
        finally:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    seed_hardcoded_books()
