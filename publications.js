const publicationContainer = document.getElementById("publication-lists");

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const citationAuthors = (authors = []) => authors.map((author) => {
  const name = escapeHtml(author);
  return author === "Liu B" ? `<strong>${name}</strong>` : name;
}).join(", ");

const publicationCategory = (work) => {
  if (work.type === "journal-article") return "Journal Articles";
  if (work.type === "conference-paper") return "Conference Papers";
  return "Preprints and Book Chapters";
};

const publicationCitation = (work) => {
  const details = [work.year, work.volume, work.issue ? `(${work.issue})` : "", work.page]
    .filter(Boolean)
    .join(work.volume ? ", " : "");
  const source = work.journal ? `<em>${escapeHtml(work.journal)}</em>` : "";
  const doi = work.doi
    ? ` <a href="https://doi.org/${encodeURIComponent(work.doi)}">doi:${escapeHtml(work.doi)}</a>`
    : "";
  return `${citationAuthors(work.authors)}. ${escapeHtml(work.title)}. ${source}${details ? `, ${escapeHtml(details)}` : ""}.${doi}`;
};

const renderPublications = (works) => {
  const categories = ["Journal Articles", "Conference Papers", "Preprints and Book Chapters"];
  publicationContainer.innerHTML = categories.map((category) => {
    const publications = works.filter((work) => publicationCategory(work) === category);
    if (!publications.length) return "";
    return `<h3>${category}</h3><ol class="pub-list">${publications
      .map((work) => `<li>${publicationCitation(work)}</li>`)
      .join("")}</ol>`;
  }).join("");
};

fetch("data/orcid-works.json")
  .then((response) => {
    if (!response.ok) throw new Error("Unable to load ORCID publication data.");
    return response.json();
  })
  .then((data) => renderPublications(data.works ?? []))
  .catch(() => {
    publicationContainer.innerHTML = '<p class="note">The publication record is temporarily unavailable. Please visit <a href="https://orcid.org/0000-0003-2683-0515">ORCID</a>.</p>';
  });
