const _store = { accessToken: null }

export const tokenStore = {
  get: () => _store.accessToken,
  set: (token) => { _store.accessToken = token },
  clear: () => { _store.accessToken = null }
}
