/**
 * Returns a safe, allowlisted iframe URL for supported media services.
 * No arbitrary HTML or third-party script code from Pages CMS is executed.
 *
 * @param {string | null | undefined} rawValue
 * @returns {{ provider: string, kind: "video" | "audio" | "document", src: string, height: number } | null}
 */
export function resolveProjectEmbed(rawValue) {
  if (typeof rawValue !== "string" || !rawValue.trim()) return null;
  // A Bandcamp embed may be copied as HTML; extract its URL without injecting the HTML.
  const original = rawValue.trim();
  const iframe = original.match(/<iframe\b[^>]*\bsrc\s*=\s*(["'])(.*?)\1/i);
  const candidate = (iframe ? iframe[2] : original).replace(/&amp;/gi, "&").trim();

  let url;
  try { url = new URL(candidate); }
  catch { return null; }
  if (!["https:", "http:"].includes(url.protocol) || url.username || url.password) return null;

  const host = url.hostname.toLowerCase();
  const parts = url.pathname.split("/").filter(Boolean);
  const oneOf = (...hosts) => hosts.includes(host);
  const videoId = /^[A-Za-z0-9_-]{11}$/;
  const driveId = /^[A-Za-z0-9_-]{10,200}$/;

  if (oneOf("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com", "youtu.be", "www.youtu.be")) {
    const id = oneOf("youtu.be", "www.youtu.be")
      ? parts[0]
      : parts[0] === "watch" ? url.searchParams.get("v")
      : ["shorts", "live", "embed", "v"].includes(parts[0]) ? parts[1] : null;
    if (id && videoId.test(id)) {
      return { provider: "YouTube", kind: "video", src: "https://www.youtube-nocookie.com/embed/" + id, height: 420 };
    }
    const list = url.searchParams.get("list");
    if ((parts[0] === "playlist" || parts[0] === "watch") && list && /^[A-Za-z0-9_-]{10,100}$/.test(list)) {
      return { provider: "YouTube", kind: "video", src: "https://www.youtube-nocookie.com/embed/videoseries?list=" + encodeURIComponent(list), height: 420 };
    }
    return null;
  }

  if (oneOf("vimeo.com", "www.vimeo.com", "player.vimeo.com")) {
    const numericParts = parts.filter((part) => /^\d{4,20}$/.test(part));
    const id = numericParts[numericParts.length - 1];
    if (!id) return null;
    const pathHash = parts[parts.lastIndexOf(id) + 1];
    const hash = url.searchParams.get("h") || (/^[a-f0-9]{6,64}$/i.test(pathHash || "") ? pathHash : null);
    if (hash && !/^[a-zA-Z0-9]{6,64}$/.test(hash)) return null;
    return {
      provider: "Vimeo", kind: "video",
      src: "https://player.vimeo.com/video/" + id + (hash ? "?h=" + encodeURIComponent(hash) : ""),
      height: 420
    };
  }

  if (oneOf("soundcloud.com", "www.soundcloud.com", "m.soundcloud.com")) {
    if (!parts.length) return null;
    const canonical = "https://soundcloud.com/" + parts.map(encodeURIComponent).join("/");
    return {
      provider: "SoundCloud", kind: "audio",
      src: "https://w.soundcloud.com/player/?url=" + encodeURIComponent(canonical) + "&color=%23c16b56&auto_play=false&hide_related=true&show_comments=false&show_user=true",
      height: parts.includes("sets") ? 450 : 166
    };
  }

  if (host === "open.spotify.com") {
    const segments = [...parts];
    if (segments[0] && /^intl-[a-z-]+$/i.test(segments[0])) segments.shift();
    if (segments[0] === "embed") segments.shift();
    const type = segments[0], id = segments[1];
    if (!["track", "album", "playlist", "artist", "episode", "show"].includes(type) || !/^[A-Za-z0-9]{10,40}$/.test(id || "")) return null;
    return { provider: "Spotify", kind: "audio", src: "https://open.spotify.com/embed/" + type + "/" + id, height: 352 };
  }

  if (oneOf("bandcamp.com", "www.bandcamp.com")) {
    if (parts[0] !== "EmbeddedPlayer") return null;
    const player = parts.join("/").match(/(?:^|\/)(album|track)=(\d{4,20})(?:\/|$)/);
    if (!player) return null;
    return {
      provider: "Bandcamp", kind: "audio",
      src: "https://bandcamp.com/EmbeddedPlayer/" + player[1] + "=" + player[2] + "/size=large/bgcol=20201e/linkcol=c16b56/transparent=true/",
      height: player[1] === "album" ? 470 : 180
    };
  }

  if (host === "drive.google.com") {
    const id = parts[0] === "file" && parts[1] === "d" ? parts[2]
      : ["open", "uc"].includes(parts[0]) ? url.searchParams.get("id") : null;
    if (!id || !driveId.test(id)) return null;
    const resourceKey = url.searchParams.get("resourcekey");
    const suffix = resourceKey && /^[A-Za-z0-9_-]{5,200}$/.test(resourceKey)
      ? "?resourcekey=" + encodeURIComponent(resourceKey) : "";
    return {
      provider: "Google Drive", kind: "document",
      src: "https://drive.google.com/file/d/" + id + "/preview" + suffix, height: 560
    };
  }

  if (host === "docs.google.com") {
    const type = parts[0], id = parts[1] === "d" ? parts[2] : null;
    if (!["document", "spreadsheets", "presentation"].includes(type) || !id || !driveId.test(id)) return null;
    return {
      provider: "Google Drive", kind: "document",
      src: "https://docs.google.com/" + type + "/d/" + id + "/" + (type === "presentation" ? "embed" : "preview"),
      height: 560
    };
  }
  return null; // Other services still work through the normal project link.
}
