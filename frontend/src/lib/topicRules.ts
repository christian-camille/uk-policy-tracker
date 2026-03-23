export function formatKeywordList(keywords: string[]): string {
  return keywords.join(", ");
}

export function parseKeywordList(input: string): string[] {
  return input
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export function ensureKeywordGroups(keywordGroups: string[][], fallbackLabel: string): string[][] {
  const normalizedGroups = keywordGroups.filter((group) => group.length > 0);
  if (normalizedGroups.length > 0) {
    return normalizedGroups;
  }

  const fallback = fallbackLabel.trim();
  return fallback ? [[fallback]] : [];
}

export function buildInitialGroupDrafts(topic: {
  keyword_groups?: string[][];
  search_queries: string[];
}): string[] {
  if (topic.keyword_groups && topic.keyword_groups.length > 0) {
    return topic.keyword_groups.map(formatKeywordList);
  }

  return [formatKeywordList(topic.search_queries)];
}